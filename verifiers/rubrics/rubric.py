from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CriterionVerdict:
    criterion_id: str
    verdict: str
    confidence: float
    reasoning: str
    raw_response: str = ""


@dataclass
class Criterion:
    id: str
    concern: str
    prompt_template: str
    allowed_verdicts: list[str]
    pass_verdicts: list[str]
    tier: str
    applies_to: list[str] = field(default_factory=lambda: ["ipi", "memory", "trd"])
    when: dict[str, Any] = field(default_factory=dict)

    def applies(self, attack_type: str, trajectory: dict[str, Any]) -> bool:
        if attack_type not in self.applies_to:
            return False
        for key, expected in self.when.items():
            actual = trajectory.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True


@dataclass
class Rubric:
    id: str
    layer: str
    description: str
    criteria: list[Criterion] = field(default_factory=list)
