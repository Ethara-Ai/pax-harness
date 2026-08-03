from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class CheckStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


class Gate(str, enum.Enum):
    ACCEPT = "ACCEPT"
    QUARANTINE = "QUARANTINE"


@dataclass
class CheckResult:
    id: str
    status: CheckStatus
    layer: str
    tier: str
    evidence: str = ""
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "layer": self.layer,
            "tier": self.tier,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }


@dataclass
class VerificationReport:
    trajectory_path: str
    case_id: str
    model: str
    recorded_score: int | None
    gate: Gate
    checks: list[CheckResult] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    judge_model: str | None = None
    duration_seconds: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def skipped(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.SKIP)

    @property
    def errored(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.ERROR)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_path": self.trajectory_path,
            "case_id": self.case_id,
            "model": self.model,
            "recorded_score": self.recorded_score,
            "gate": self.gate.value,
            "judge_model": self.judge_model,
            "duration_seconds": round(self.duration_seconds, 3),
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "errored": self.errored,
                "total": len(self.checks),
            },
            "checks": [c.to_dict() for c in self.checks],
            "findings": self.findings,
        }
