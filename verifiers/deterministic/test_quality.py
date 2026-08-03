from verifiers.deterministic.predicates import (
    check_correction_integrity,
    check_no_obvious_fake_domain,
)
from verifiers.schemas import CheckStatus


def test_no_obvious_fake_domain(trajectory, dataset_case):
    result = check_no_obvious_fake_domain(trajectory, dataset_case)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence


def test_correction_integrity(trajectory):
    result = check_correction_integrity(trajectory)
    if result.status == CheckStatus.SKIP:
        return
    assert result.status == CheckStatus.PASS, result.evidence
