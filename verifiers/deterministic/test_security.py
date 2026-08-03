from verifiers.deterministic.predicates import check_no_live_arns, check_no_machine_paths
from verifiers.schemas import CheckStatus


def test_no_machine_paths(trajectory):
    result = check_no_machine_paths(trajectory)
    assert result.status == CheckStatus.PASS, result.evidence


def test_no_live_arns(trajectory):
    result = check_no_live_arns(trajectory)
    assert result.status == CheckStatus.PASS, result.evidence
