"""Scoped checks over curator-transcribed PUBLIC facts; no label inference."""

from __future__ import annotations

import math
from typing import Any

import pint

from chemfeasbench.schemas.models import CheckResult, CheckSpec, PublicInput

UNITS = pint.UnitRegistry()
Q = UNITS.Quantity


def number(value: Any, unit: str | None = None) -> float:
    q = Q(value)
    n = float(q.to(unit).magnitude if unit else q.to_base_units().magnitude)
    if not math.isfinite(n):
        raise ValueError("Nonfinite quantity")
    return n


def check(spec: CheckSpec) -> CheckResult:
    base: dict[str, Any] = dict(
        check_name=spec.name,
        inputs=spec.inputs,
        applicability=spec.applicable,
        assumptions=spec.assumptions,
    )
    if spec.applicable is False:
        return CheckResult(
            **base, result="not_applicable", evidence="Applicability explicitly excluded."
        )
    if spec.applicable is None:
        return CheckResult(
            **base,
            result="unknown",
            evidence="Applicability is not established.",
            uncertainty="Scope unknown",
        )
    a: Any
    b: Any
    x = spec.inputs
    try:
        verdict: bool | None
        if spec.name == "dimension":
            a, b = Q(x["quantity"]), Q(x["required_unit"])
            verdict = a.dimensionality == b.dimensionality
            evidence = f"Dimensions: {a.dimensionality}; required {b.dimensionality}."
        elif spec.name == "dilution":
            stock = number(x["stock"], "mole/liter")
            aliquot, final = number(x["aliquot"], "liter"), number(x["final_volume"], "liter")
            declared = number(x["declared"], "mole/liter")
            if min(stock, aliquot, final, declared) <= 0 or aliquot > final:
                raise ValueError("Impossible or nonpositive dilution inputs")
            expected = stock * aliquot / final
            verdict = math.isclose(
                expected, declared, rel_tol=float(x.get("relative_tolerance", 0.01))
            )
            evidence = (
                f"Cstock × Valiquot / Vfinal = {expected:g} mol/L; declared {declared:g} mol/L."
            )
        elif spec.name == "balance":
            # Explicit equivalents: upper bound only; never proof of synthesis or yield.
            inputs = x["reactants"]
            product = number(x["product_amount"], "mole")
            coefficient = float(x["product_coefficient"])
            if product < 0 or coefficient <= 0 or not inputs:
                raise ValueError("Invalid material balance inputs")
            limits = []
            for item in inputs:
                amount, coef = number(item["amount"], "mole"), float(item["coefficient"])
                if amount < 0 or coef <= 0:
                    raise ValueError("Invalid reactant amounts or coefficients")
                limits.append(amount / coef)
            maximum = min(limits) * coefficient
            verdict = product <= maximum * (1 + float(x.get("relative_tolerance", 0.01)))
            evidence = (
                f"Stoichiometric upper bound {maximum:g} mol; declared product {product:g} mol."
            )
        elif spec.name == "spectral_overlap":
            a = [number(v, "nm") for v in x["signal_range"]]
            b = [number(v, "nm") for v in x["instrument_range"]]
            if len(a) != 2 or len(b) != 2 or not (0 < a[0] < a[1] and 0 < b[0] < b[1]):
                raise ValueError("Invalid spectral bounds")
            width = min(a[1], b[1]) - max(a[0], b[0])
            verdict = width > 0
            evidence = f"Supported overlap width {max(0, width):g} nm. Overlap alone does not establish sensitivity."
        elif spec.name == "calibration_range":
            a, b = [number(v) for v in x["range"]]
            value = number(x["sample"])
            units = [Q(v).dimensionality for v in [*x["range"], x["sample"]]]
            if len(set(map(str, units))) != 1 or a >= b:
                raise ValueError("Invalid calibration dimensions or order")
            verdict = a <= value <= b
            evidence = f"Sample {value:g}; validated interval [{a:g}, {b:g}] in base units."
        elif spec.name == "threshold":
            a, b = Q(x["value"]), Q(x["bound"])
            b = b.to(a.units)
            if not math.isfinite(float(a.magnitude)) or not math.isfinite(float(b.magnitude)):
                raise ValueError("Nonfinite threshold input")
            operators = {
                "<": lambda: a < b,
                "<=": lambda: a <= b,
                ">": lambda: a > b,
                ">=": lambda: a >= b,
                "==": lambda: a == b,
            }
            verdict = bool(operators[x["operator"]]())
            evidence = f"{a} {x['operator']} {b}: {verdict}; criterion supplied by the case."
        else:
            required, observed = x["required"], x["observed"]
            if not required or not x.get("scope_justification"):
                raise ValueError("A scoped evidence requirement is mandatory")
            values = [observed.get(k) for k in required]
            if any(v not in (True, False, None) for v in values):
                raise ValueError("Evidence presence must be true, false or null")
            verdict = False if False in values else (None if None in values else True)
            evidence = "Explicit evidence inventory: " + ", ".join(
                f"{k}={observed.get(k)}" for k in required
            )
        return CheckResult(
            **base,
            result="unknown" if verdict is None else ("satisfied" if verdict else "violated"),
            evidence=evidence,
            uncertainty="Required evidence status unspecified" if verdict is None else None,
        )
    except (KeyError, TypeError, ValueError, ZeroDivisionError, pint.errors.PintError) as exc:
        return CheckResult(
            **base,
            result="unknown",
            evidence="Insufficient or unsupported structured inputs.",
            uncertainty=type(exc).__name__,
        )


def audit(public: PublicInput) -> list[CheckResult]:
    return [check(s) for s in public.structured_checks]
