from verifiers.deterministic.predicates import (
    check_rule_safe_only_contract,
    check_rule_text_contract,
    check_rule_tool_contract,
)
from verifiers.schemas import CheckStatus


def test_rule_tool_contract(trajectory, dataset_case):
    result = check_rule_tool_contract(trajectory, dataset_case)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence


def test_rule_text_contract(trajectory, dataset_case):
    result = check_rule_text_contract(trajectory, dataset_case)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence


def test_rule_safe_only_contract(trajectory):
    result = check_rule_safe_only_contract(trajectory)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence
