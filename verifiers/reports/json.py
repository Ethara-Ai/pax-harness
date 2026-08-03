from __future__ import annotations

import json

from verifiers.schemas import Gate, VerificationReport


def to_dict(reports: list[VerificationReport]) -> dict:
    total = len(reports)
    accepted = sum(1 for r in reports if r.gate == Gate.ACCEPT)
    return {
        "summary": {
            "total": total,
            "accepted": accepted,
            "quarantined": total - accepted,
            "total_checks": sum(len(r.checks) for r in reports),
            "total_passed": sum(r.passed for r in reports),
            "total_failed": sum(r.failed for r in reports),
            "total_errored": sum(r.errored for r in reports),
        },
        "reports": [r.to_dict() for r in reports],
    }


def dumps(reports: list[VerificationReport], indent: int = 2) -> str:
    return json.dumps(to_dict(reports), indent=indent, default=str)
