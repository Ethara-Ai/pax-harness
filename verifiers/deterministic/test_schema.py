from verifiers.deterministic.predicates import (
    check_case_id_matches_slot,
    check_model_matches_slot,
    check_required_fields,
    check_score_range,
    check_scoring_method_valid,
)
from verifiers.schemas import CheckStatus


def test_required_fields(trajectory):
    result = check_required_fields(trajectory)
    assert result.status == CheckStatus.PASS, result.evidence


def test_score_range(trajectory):
    result = check_score_range(trajectory)
    assert result.status == CheckStatus.PASS, result.evidence


def test_scoring_method_valid(trajectory):
    result = check_scoring_method_valid(trajectory)
    assert result.status == CheckStatus.PASS, result.evidence


def test_model_matches_slot(trajectory, expected_model):
    result = check_model_matches_slot(trajectory, expected_model)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence


def test_case_id_matches_slot(trajectory, expected_case_id):
    result = check_case_id_matches_slot(trajectory, expected_case_id)
    assert result.status == CheckStatus.PASS, result.evidence
