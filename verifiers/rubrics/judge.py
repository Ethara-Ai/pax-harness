from __future__ import annotations

import json
import os
import re
from typing import Any

import litellm

from verifiers.rubrics.rubric import Criterion, CriterionVerdict, Rubric
from verifiers.schemas import CheckResult, CheckStatus


CROSS_MODEL_JUDGES = {
    "claude-opus": "gpt-5.6-sol",
    "gpt-5.6-sol": "claude-opus-5",
    "gpt-5-6-sol": "claude-opus-5",
}


CC_MODEL_PREFIX = "claude-"
CODEX_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4", "codex-")
DEFAULT_CC_BRIDGE = "http://127.0.0.1:8765"
DEFAULT_CODEX_BRIDGE = "http://127.0.0.1:8788"


def select_judge_model(generator_model: str, override: str | None = None) -> str:
    if override:
        return override
    lowered = generator_model.lower()
    if lowered.startswith("claude-opus"):
        return CROSS_MODEL_JUDGES["claude-opus"]
    if lowered.startswith("gpt-5.6-sol") or lowered.startswith("gpt-5-6-sol"):
        return CROSS_MODEL_JUDGES["gpt-5.6-sol"]
    raise ValueError(
        f"No auto-judge rule for generator model {generator_model!r}. "
        f"Pass --judge explicitly (e.g. --judge cc-opus or --judge ccx)."
    )


def _configure_provider_env(judge_model: str) -> str:
    lowered = judge_model.lower()
    if lowered.startswith(CC_MODEL_PREFIX):
        os.environ.setdefault("ANTHROPIC_API_KEY", "pax-cc-stub")
        os.environ.setdefault("ANTHROPIC_API_BASE", DEFAULT_CC_BRIDGE)
        return f"anthropic/{judge_model}"
    if lowered.startswith(CODEX_MODEL_PREFIXES):
        os.environ.setdefault("OPENAI_API_KEY", "pax-ccx-stub")
        os.environ.setdefault("OPENAI_BASE_URL", DEFAULT_CODEX_BRIDGE)
        return f"openai/{judge_model}"
    return judge_model


def _render_prompt(template: str, context: dict[str, Any]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        value = context.get(key, "")
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2, default=str)
        return str(value)

    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace, template)


def _parse_verdict(raw: str, allowed: list[str]) -> tuple[str, float, str]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    obj = None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                obj = None
    if not isinstance(obj, dict):
        for verdict in allowed:
            if verdict.lower() in raw.lower():
                return verdict, 0.4, "verdict extracted from prose"
        return "UNKNOWN", 0.0, f"could not parse judge response: {raw[:200]}"
    verdict = str(obj.get("verdict", "UNKNOWN")).upper()
    if verdict not in [v.upper() for v in allowed]:
        return "UNKNOWN", 0.0, f"verdict {verdict!r} not in allowed set {allowed}"
    canonical = next(v for v in allowed if v.upper() == verdict)
    try:
        confidence = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    reasoning = str(obj.get("reasoning", ""))
    return canonical, confidence, reasoning


def _build_prompt(criterion: Criterion, context: dict[str, Any]) -> str:
    body = _render_prompt(criterion.prompt_template, context)
    schema_hint = (
        "\n\nRespond with ONLY a single JSON object with keys "
        f"'verdict' (one of {criterion.allowed_verdicts}), "
        "'confidence' (float 0.0-1.0), and 'reasoning' (one to three sentences)."
    )
    return body + schema_hint


def evaluate_criterion(
    criterion: Criterion,
    context: dict[str, Any],
    judge_model: str,
    max_tokens: int = 512,
    temperature: float = 0.0,
) -> CriterionVerdict:
    routed = _configure_provider_env(judge_model)
    prompt = _build_prompt(criterion, context)
    response = litellm.completion(
        model=routed,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    raw = response.choices[0].message.content or ""
    verdict, confidence, reasoning = _parse_verdict(raw, criterion.allowed_verdicts)
    return CriterionVerdict(
        criterion_id=criterion.id,
        verdict=verdict,
        confidence=confidence,
        reasoning=reasoning,
        raw_response=raw,
    )


def evaluate_rubric(
    rubric: Rubric,
    context: dict[str, Any],
    attack_type: str,
    trajectory: dict[str, Any],
    judge_model: str,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for criterion in rubric.criteria:
        if not criterion.applies(attack_type, trajectory):
            results.append(CheckResult(
                id=criterion.concern,
                status=CheckStatus.SKIP,
                layer=rubric.layer,
                tier=criterion.tier,
                reasoning="criterion does not apply to this trajectory",
            ))
            continue
        try:
            verdict = evaluate_criterion(criterion, context, judge_model)
            status = (
                CheckStatus.PASS
                if verdict.verdict in criterion.pass_verdicts
                else CheckStatus.FAIL
            )
            results.append(CheckResult(
                id=criterion.concern,
                status=status,
                layer=rubric.layer,
                tier=criterion.tier,
                evidence=f"verdict={verdict.verdict} confidence={verdict.confidence:.2f}",
                reasoning=verdict.reasoning,
                metadata={
                    "verdict": verdict.verdict,
                    "confidence": verdict.confidence,
                    "raw_response": verdict.raw_response[:2000],
                },
            ))
        except Exception as exc:
            results.append(CheckResult(
                id=criterion.concern,
                status=CheckStatus.ERROR,
                layer=rubric.layer,
                tier=criterion.tier,
                reasoning=f"judge call failed: {type(exc).__name__}: {exc}",
            ))
    return results
