"""Accessible HTML and vector figures generated only from captured scored runs."""

from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from chemfeasbench.artifacts.io import lock, read_json, seal, verify
from chemfeasbench.schemas.models import LABELS


def _report(run: Path) -> Path:
    verify(run)
    target = run / "report.html"
    summary_path = run / "summary.json"
    style = "body{font:16px/1.6 system-ui;max-width:1080px;margin:40px auto;padding:0 24px;color:#153149;background:#f8fafb}h1{font-size:34px}h2{margin-top:36px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border:1px solid #cbd5df;text-align:left}th{background:#e8f0f3}.notice{padding:18px;background:#fff0cc;border-left:5px solid #a36b0a}img{max-width:100%}code{overflow-wrap:anywhere}"
    if not summary_path.exists():
        content = '<h1>ChemFeasBench research report</h1><p class="notice">No scored observations. No scientific results are available.</p>'
    else:
        s = read_json(summary_path)
        m = s["metrics"]
        labels = [*LABELS, "format_failure", "provider_error", "abstention", "missing"]
        matrix = np.array([[m["confusion_matrix"][a][b] for b in labels] for a in LABELS])
        fig, ax = plt.subplots(figsize=(11, 4.6), constrained_layout=True)
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, int(matrix.max())))
        ax.set_xticks(
            range(len(labels)), [label.replace("_", "\n") for label in labels], fontsize=8
        )
        ax.set_yticks(range(4), [label.replace("_", " ") for label in LABELS], fontsize=9)
        for y in range(4):
            for x in range(len(labels)):
                ax.text(
                    x,
                    y,
                    str(matrix[y, x]),
                    ha="center",
                    va="center",
                    color="white" if matrix[y, x] > 0.6 * max(1, matrix.max()) else "#153149",
                )
        ax.set_xlabel("Prediction or output failure")
        ax.set_ylabel("Reference label")
        ax.set_title("Observed confusion counts · " + s["scientific_status"], fontsize=10)
        fig.savefig(run / "confusion.svg")
        fig.savefig(run / "confusion.png", dpi=220)
        plt.close(fig)
        bins = [b for b in m["calibration"]["bins"] if b["n"]]
        fig, ax = plt.subplots(figsize=(5, 4), constrained_layout=True)
        ax.plot([0, 1], [0, 1], ls="--", color="#667")
        if bins:
            ax.scatter(
                [b["mean_confidence"] for b in bins],
                [b["accuracy"] for b in bins],
                s=[30 + 10 * b["n"] for b in bins],
                color="#137f84",
            )
            for b in bins:
                ax.annotate(
                    f"n={b['n']}",
                    (b["mean_confidence"], b["accuracy"]),
                    xytext=(5, 6),
                    textcoords="offset points",
                    fontsize=8,
                )
        else:
            ax.text(0.5, 0.5, "No valid probability outputs", ha="center")
        ax.set(
            xlim=(-0.03, 1.03),
            ylim=(-0.03, 1.03),
            xlabel="Mean reported confidence",
            ylabel="Observed accuracy",
            title="Calibration · parsed outputs only",
        )
        fig.savefig(run / "calibration.svg")
        plt.close(fig)
        metric_rows = ""
        for key in [
            "macro_f1",
            "major_failure_recall",
            "false_acceptance_rate",
            "missed_major_failure_rate",
            "format_failure_rate",
        ]:
            val = m[key]
            value = val["value"] if isinstance(val, dict) else val
            display = "Not estimable" if value is None else f"{value:.3f}"
            den = (
                f"{val['numerator']} / {val['denominator']}"
                if isinstance(val, dict)
                else f"4 labels; {m['n']} tasks"
            )
            ci = s["primary_intervals"].get(key, {}).get("ci95")
            metric_rows += f'<tr><th scope="row">{html.escape(key.replace("_", " "))}</th><td>{display}</td><td>{den}</td><td>{html.escape(str(ci)) if ci else "Not estimable"}</td></tr>'
        confusion = (
            '<table><caption>Confusion counts; output failures remain in the reference denominators</caption><tr><th scope="col">Reference</th>'
            + "".join(f'<th scope="col">{html.escape(label)}</th>' for label in labels)
            + "</tr>"
        )
        for label in LABELS:
            confusion += (
                '<tr><th scope="row">'
                + html.escape(label)
                + "</th>"
                + "".join(f"<td>{m['confusion_matrix'][label][p]}</td>" for p in labels)
                + "</tr>"
            )
        confusion += "</table>"
        content = f"""<header><p>CHEMICAL EXPERIMENTAL VALIDITY</p><h1>ChemFeasBench · Research report</h1></header>
<p class="notice"><strong>{html.escape(s["scientific_status"])}</strong><br>Observed software smoke results are not a validated chemistry ranking.</p>
<p>Model: <strong>{html.escape(s["model"]["model"])}</strong> · Condition: {html.escape(s["condition"])}<br>{m["n"]} tasks in {m["clusters"]} connected family clusters.</p>
<h2>Classification</h2><table><caption>Primary outcomes and output reliability</caption><tr><th>Metric</th><th>Estimate</th><th>Denominator</th><th>95% cluster interval</th></tr>{metric_rows}</table>
<p>Macro-F1 averages all four labels. Invalid, missing and abstained outputs receive no classification credit. A null interval denotes insufficient clusters or an undefined resampled denominator.</p>
<img src="confusion.svg" alt="Confusion heatmap; all values appear in the following table">{confusion}
<h2>Confidence and diagnosis</h2><img src="calibration.svg" alt="Calibration of parsed outputs, with counts on each occupied bin">
<p>Brier score (parsed outputs): {html.escape(str(m["brier_parsed_only"]))}. Failure-penalized Brier: {html.escape(str(m["brier_failure_penalty"]))}.</p>
<pre>{html.escape(json.dumps(s["diagnosis"], indent=2))}</pre>
<p>Human explanation accuracy is reported only for actual independently assessed explanations with consensus. A zero denominator means no such assessment is available. Correct issue codes and quote overlap alone are structural proxies.</p>
<h2>Resources</h2><pre>{html.escape(json.dumps(s["usage"], indent=2))}</pre>
<h2>Interpretation limits</h2><ul>{"".join("<li>" + html.escape(x) + "</li>" for x in s["limitations"])}</ul>
<p>Sampling intervals do not represent all uncertainty in annotation, contamination, model sampling or generalization. Small pilot results should guide curation, not competitive claims.</p>
<h2>Traceability</h2><p>Run fingerprint: <code>{s["run_id"]}</code></p><p>Raw requests, responses, failure records and checksums are retained in the private run bundle.</p>"""
    target.write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChemFeasBench research report</title><style>{style}</style></head><body>{content}</body></html>'
    )
    seal(run)
    return target


def report(run: Path) -> Path:
    with lock(run / ".run.lock"):
        return _report(run)
