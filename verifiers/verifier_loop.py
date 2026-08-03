from __future__ import annotations

from pathlib import Path

from verifiers.evaluator import EvaluatorOptions, verify_trajectory
from verifiers.schemas import VerificationReport


TRAJECTORY_GLOB = "**/*.json"


def find_trajectory_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    files = []
    for path in sorted(root.rglob("*.json")):
        stem = path.stem
        if stem in ("hard_benchmark_summary", "trd_benchmark_summary", "selection_rationale"):
            continue
        parent = path.parent.name
        if parent in ("glm", "nova", "results"):
            files.append(path)
            continue
        if stem.startswith(("ipi_", "mem_", "trd_")):
            files.append(path)
    return files


def verify_directory(root: Path, options: EvaluatorOptions) -> list[VerificationReport]:
    reports = []
    for path in find_trajectory_files(root):
        reports.append(verify_trajectory(path, options))
    return reports
