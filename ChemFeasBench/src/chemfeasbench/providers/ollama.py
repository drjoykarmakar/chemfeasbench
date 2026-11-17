"""Pinned local Ollama adapter. No remote provider or model substitution."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from chemfeasbench.artifacts.io import canonical
from chemfeasbench.schemas.models import RunConfig


class Ollama:
    def __init__(self, config: RunConfig, client: httpx.Client | None = None):
        self.config = config
        url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        parsed = urlsplit(url)
        if (
            parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.scheme != "http"
            or parsed.username
            or parsed.password
            or parsed.query
        ):
            raise ValueError("This adapter permits a local loopback Ollama endpoint only")
        self.client = client or httpx.Client(
            base_url=url, trust_env=False, follow_redirects=False, timeout=config.timeout_seconds
        )

    def close(self) -> None:
        self.client.close()

    def metadata(self) -> dict[str, Any]:
        response = self.client.get("/api/tags", timeout=10)
        response.raise_for_status()
        entry = next(
            (m for m in response.json().get("models", []) if m["name"] == self.config.model), None
        )
        if (
            entry is None
            or entry.get("digest", "").removeprefix("sha256:") != self.config.model_digest
        ):
            raise ValueError(
                "Requested local model unavailable or digest mismatch; no model substituted"
            )
        version = self.client.get("/api/version", timeout=10)
        version.raise_for_status()
        return {
            "provider": "ollama",
            "model": entry["name"],
            "digest": entry["digest"],
            "details": entry.get("details", {}),
            "runtime_version": version.json()["version"],
            "cost_usd": None,
            "cost_note": "Local compute and energy costs not measured.",
        }

    def payload(self, request: dict[str, Any], seed: int) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "prompt": canonical(request),
            "format": request["output_schema"],
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": self.config.temperature,
                "seed": seed,
                "num_predict": self.config.max_output_tokens,
                "num_ctx": self.config.context_window,
                "num_thread": self.config.cpu_threads,
            },
        }

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.metadata()  # Fail closed if tag changes during a run.
        start = time.perf_counter()
        with self.client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > 2_000_000:
                    raise ValueError("Provider response exceeds transport size limit")
        import json

        data = json.loads(raw)
        if data.get("done") is not True or not isinstance(data.get("response"), str):
            raise ValueError("Incomplete provider envelope")
        return {
            "raw_response": data["response"],
            "provider_envelope": data,
            "elapsed_seconds": time.perf_counter() - start,
            "input_tokens": data.get("prompt_eval_count"),
            "output_tokens": data.get("eval_count"),
            "cost_usd": None,
            "finish_reason": data.get("done_reason"),
        }
