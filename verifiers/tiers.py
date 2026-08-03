from __future__ import annotations

import enum

from verifiers.schemas import CheckResult, CheckStatus, Gate


class Tier(str, enum.Enum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    ADVISORY = "ADVISORY"


def compute_gate(checks: list[CheckResult]) -> Gate:
    for check in checks:
        if check.status == CheckStatus.FAIL and check.tier == Tier.BLOCKER.value:
            return Gate.QUARANTINE
        if check.status == CheckStatus.ERROR and check.tier == Tier.BLOCKER.value:
            return Gate.QUARANTINE
    return Gate.ACCEPT
