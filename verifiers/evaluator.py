from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verifiers.deterministic.predicates import run_all_deterministic_checks
from verifiers.rubrics.judge import evaluate_rubric, select_judge_model
from verifiers.rubrics.loader import load_all_rubrics
from verifiers.schemas import CheckResult, CheckStatus, Gate, VerificationReport
from verifiers.tiers import compute_gate


ATTACK_TYPE_PREFIX = {"ipi": "ipi", "mem": "memory", "trd": "trd"}
DATASET_SUBDIRS = {"ipi": "ipi_cases", "memory": "memory_cases", "trd": "trd_cases"}
SLOT_MODEL_MAP = {"glm": "glm-5", "nova": "nova-2-lite"}


@dataclass
class EvaluatorOptions:
    dataset_root: Path | None = None
    workspace_root: Path | None = None
    skip_rubrics: bool = False
    skip_deterministic: bool = False
    judge_override: str | None = None
    judge_max_rubrics: int | None = None


def _infer_attack_type(case_id: str) -> str:
    prefix = case_id.split("_", 1)[0]
    return ATTACK_TYPE_PREFIX.get(prefix, "unknown")


def _locate_dataset_case(case_id: str, dataset_root: Path | None) -> dict[str, Any] | None:
    if dataset_root is None:
        return None
    attack_type = _infer_attack_type(case_id)
    subdir = DATASET_SUBDIRS.get(attack_type)
    if subdir is None:
        return None
    idx = case_id.split("_", 1)[1] if "_" in case_id else ""
    for candidate in (dataset_root / subdir / f"case_{idx}.json",
                      dataset_root / subdir / f"{case_id}.json"):
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
    return None


def _load_credentials(dataset_root: Path | None) -> list[dict[str, Any]] | None:
    if dataset_root is None:
        return None
    for candidate in (dataset_root / "mock_credentials.json",
                      dataset_root.parent / "mock_credentials.json"):
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
    return None


def _build_rubric_context(trajectory: dict[str, Any],
                          dataset_case: dict[str, Any] | None,
                          attack_type: str) -> dict[str, Any]:
    tool_calls = trajectory.get("tool_calls_detected", []) or []
    tool_calls_summary = "\n".join(
        f"- {tc.get('name', '?')}({tc.get('arguments', '')[:200]}...)"
        for tc in tool_calls
    ) or "(none)"
    assistant_text = []
    for msg in trajectory.get("full_trace", []) or []:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                assistant_text.append(content)
    final_text = "\n\n---\n\n".join(assistant_text)[-4000:] or "(no assistant text)"
    dc = dataset_case or {}
    return {
        "attack_type": attack_type,
        "technique": dc.get("technique") or dc.get("technique_name", "unknown"),
        "target_tool": dc.get("target_tool", "n/a"),
        "target_domain": (dc.get("success_indicators") or ["n/a"])[0],
        "expected_action": dc.get("expected_action", "n/a"),
        "recorded_score": trajectory.get("score"),
        "scoring_method": trajectory.get("scoring_method"),
        "tool_calls": tool_calls_summary,
        "assistant_text": final_text,
        "injection_template": dc.get("injection_template") or dc.get("attack_prompt", ""),
    }


def verify_trajectory(trajectory_path: Path, options: EvaluatorOptions) -> VerificationReport:
    start = time.time()
    with open(trajectory_path) as f:
        trajectory = json.load(f)

    case_id = trajectory.get("case_id", trajectory_path.stem)
    model = trajectory.get("model", "unknown")
    recorded_score = trajectory.get("score")
    slot = trajectory_path.parent.name
    expected_model = SLOT_MODEL_MAP.get(slot)
    expected_case_id = trajectory_path.stem
    dataset_case = _locate_dataset_case(case_id, options.dataset_root)
    attack_type = _infer_attack_type(case_id)

    checks: list[CheckResult] = []
    findings: list[str] = []
    judge_model: str | None = None

    if not options.skip_deterministic:
        credentials = _load_credentials(options.dataset_root)
        checks.extend(run_all_deterministic_checks(
            trajectory=trajectory,
            dataset_case=dataset_case,
            expected_model=expected_model,
            expected_case_id=expected_case_id,
            workspace_root=options.workspace_root,
            credentials=credentials,
        ))

    if not options.skip_rubrics:
        try:
            judge_model = select_judge_model(model, options.judge_override)
        except ValueError as e:
            findings.append(f"rubric layer skipped: {e}")
        if judge_model is not None:
            context = _build_rubric_context(trajectory, dataset_case, attack_type)
            rubrics = load_all_rubrics()
            if options.judge_max_rubrics is not None:
                rubrics = rubrics[:options.judge_max_rubrics]
            for rubric in rubrics:
                checks.extend(evaluate_rubric(
                    rubric=rubric,
                    context=context,
                    attack_type=attack_type,
                    trajectory=trajectory,
                    judge_model=judge_model,
                ))

    for check in checks:
        if check.status in (CheckStatus.FAIL, CheckStatus.ERROR):
            findings.append(f"[{check.tier}] {check.id}: {check.evidence or check.reasoning}")

    gate = compute_gate(checks)
    return VerificationReport(
        trajectory_path=str(trajectory_path),
        case_id=case_id,
        model=model,
        recorded_score=recorded_score,
        gate=gate,
        checks=checks,
        findings=findings,
        judge_model=judge_model,
        duration_seconds=time.time() - start,
    )
