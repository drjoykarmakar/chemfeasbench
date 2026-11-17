import pytest

from chemfeasbench.constraints.engine import check, number
from chemfeasbench.schemas.models import CheckSpec


def spec(name, inputs, applicable=True):
    return CheckSpec(
        name=name,
        inputs=inputs,
        applicable=applicable,
        source_quotes=["synthetic fixture"],
        assumptions=["test only"],
    )


def test_units():
    assert number("1 millimole/liter", "micromole/liter") == pytest.approx(1000)
    assert number("1000 nanometer", "micrometer") == pytest.approx(1)


@pytest.mark.parametrize(
    "value,expected",
    [("10 micromole/liter", "satisfied"), ("100 micromole/liter", "violated"), (None, "unknown")],
)
def test_dilution(value, expected):
    assert (
        check(
            spec(
                "dilution",
                {
                    "stock": "10 millimole/liter",
                    "aliquot": "1 microliter",
                    "final_volume": "1 milliliter",
                    "declared": value,
                },
            )
        ).result
        == expected
    )


@pytest.mark.parametrize(
    "applicable,result", [(None, "unknown"), (False, "not_applicable"), (True, "unknown")]
)
def test_missing_and_inapplicable(applicable, result):
    assert check(spec("dilution", {}, applicable)).result == result


@pytest.mark.parametrize(
    "bounds,expected",
    [
        (["490 nm", "510 nm"], "satisfied"),
        (["600 nm", "620 nm"], "violated"),
        (["500 nm", "520 nm"], "violated"),
        (None, "unknown"),
    ],
)
def test_overlap(bounds, expected):
    assert (
        check(
            spec(
                "spectral_overlap",
                {"signal_range": ["480 nm", "500 nm"], "instrument_range": bounds},
            )
        ).result
        == expected
    )


def test_range_units_and_threshold():
    assert (
        check(
            spec(
                "calibration_range",
                {
                    "range": ["1 micromole/liter", "10 micromole/liter"],
                    "sample": "0.005 millimole/liter",
                },
            )
        ).result
        == "satisfied"
    )
    assert (
        check(
            spec("threshold", {"value": "500 nm", "bound": "0.6 micrometer", "operator": "<"})
        ).result
        == "satisfied"
    )
    assert (
        check(spec("threshold", {"value": "500 nm", "bound": "0.6 second", "operator": "<"})).result
        == "unknown"
    )


def test_balance_only_upper_bound():
    result = check(
        spec(
            "balance",
            {
                "reactants": [{"amount": "2 millimole", "coefficient": 2}],
                "product_amount": "1.2 millimole",
                "product_coefficient": 1,
            },
        )
    )
    assert result.result == "violated"


def test_dimension_failure():
    assert (
        check(spec("dimension", {"quantity": "3 second", "required_unit": "meter"})).result
        == "violated"
    )


@pytest.mark.parametrize(
    "observed,result",
    [({"blank": True}, "satisfied"), ({"blank": False}, "violated"), ({}, "unknown")],
)
def test_scoped_evidence(observed, result):
    assert (
        check(
            spec(
                "required_evidence",
                {
                    "required": ["blank"],
                    "observed": observed,
                    "scope_justification": "Explicit blank-subtracted objective",
                },
            )
        ).result
        == result
    )


def test_no_universal_control_rule():
    assert (
        check(
            spec("required_evidence", {"required": ["blank"], "observed": {"blank": False}})
        ).result
        == "unknown"
    )


def test_nonfinite_threshold_unknown():
    assert (
        check(spec("threshold", {"value": "nan meter", "bound": "1 meter", "operator": "<"})).result
        == "unknown"
    )
