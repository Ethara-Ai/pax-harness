from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required for rubric loading. Install with `pip install pyyaml`."
    ) from exc

from verifiers.rubrics.rubric import Criterion, Rubric


RUBRIC_DIR = Path(__file__).parent


def _build_criterion(data: dict[str, Any]) -> Criterion:
    return Criterion(
        id=data["id"],
        concern=data["concern"],
        prompt_template=data["prompt"],
        allowed_verdicts=list(data["allowed_verdicts"]),
        pass_verdicts=list(data["pass_verdicts"]),
        tier=data.get("tier", "MAJOR"),
        applies_to=list(data.get("applies_to", ["ipi", "memory", "trd"])),
        when=dict(data.get("when", {})),
    )


def load_rubric(path: Path) -> Rubric:
    with open(path) as f:
        data = yaml.safe_load(f)
    criteria = [_build_criterion(c) for c in data.get("criteria", [])]
    return Rubric(
        id=data["id"],
        layer=data["layer"],
        description=data.get("description", ""),
        criteria=criteria,
    )


def load_all_rubrics(directory: Path | None = None) -> list[Rubric]:
    root = directory or RUBRIC_DIR
    rubrics = []
    for path in sorted(root.glob("*.yaml")):
        rubrics.append(load_rubric(path))
    return rubrics
