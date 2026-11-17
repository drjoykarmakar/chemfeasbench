"""Operational label precedence for explicit, independently justified judgments."""

from chemfeasbench.schemas.models import Label


def decide(*, demonstrated_major: bool, critical_unknown: bool, demonstrated_minor: bool) -> Label:
    if demonstrated_major:
        return "major_validity_failure"
    if critical_unknown:
        return "insufficient_information"
    if demonstrated_minor:
        return "minor_issue"
    return "valid"
