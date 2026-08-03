from verifiers.deterministic.predicates import check_carrier_file_exists
from verifiers.schemas import CheckStatus


def test_carrier_file_exists(dataset_case, workspace_root):
    result = check_carrier_file_exists(dataset_case, workspace_root)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence
