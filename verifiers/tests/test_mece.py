from __future__ import annotations

import pytest

from verifiers.concerns import CONCERNS, CONCERNS_BY_ID, Owner
from verifiers.deterministic.predicates import PREDICATE_CHECK_IDS
from verifiers.rubrics.loader import load_all_rubrics


def _rubric_concern_ids() -> set[str]:
    ids = set()
    for rubric in load_all_rubrics():
        for criterion in rubric.criteria:
            ids.add(criterion.concern)
    return ids


DETERMINISTIC_CONCERNS = {c.id for c in CONCERNS if c.owner == Owner.DETERMINISTIC}
RUBRIC_CONCERNS_DECLARED = {c.id for c in CONCERNS if c.owner == Owner.RUBRIC}


def test_registry_has_no_duplicate_ids():
    ids = [c.id for c in CONCERNS]
    assert len(ids) == len(set(ids)), (
        f"duplicate concern ids in registry: "
        f"{[i for i in ids if ids.count(i) > 1]}"
    )


def test_no_predicate_orphans():
    orphans = PREDICATE_CHECK_IDS - CONCERNS_BY_ID.keys()
    assert not orphans, (
        f"predicates emit check_ids not in concerns registry: {sorted(orphans)}. "
        f"Either add them to CONCERNS or fix the predicate id."
    )


def test_no_rubric_orphans():
    rubric_ids = _rubric_concern_ids()
    orphans = rubric_ids - CONCERNS_BY_ID.keys()
    assert not orphans, (
        f"rubric criteria reference concerns not in registry: {sorted(orphans)}. "
        f"Either add them to CONCERNS or fix the criterion.concern field."
    )


def test_deterministic_concerns_all_implemented():
    unimplemented = DETERMINISTIC_CONCERNS - PREDICATE_CHECK_IDS
    assert not unimplemented, (
        f"concerns marked DETERMINISTIC but no predicate emits them: {sorted(unimplemented)}. "
        f"Either implement a predicate or change the concern owner."
    )


def test_rubric_concerns_all_implemented():
    rubric_ids = _rubric_concern_ids()
    unimplemented = RUBRIC_CONCERNS_DECLARED - rubric_ids
    assert not unimplemented, (
        f"concerns marked RUBRIC but no criterion implements them: {sorted(unimplemented)}. "
        f"Either add a criterion or change the concern owner."
    )


def test_mutual_exclusivity():
    rubric_ids = _rubric_concern_ids()
    overlap = PREDICATE_CHECK_IDS & rubric_ids
    assert not overlap, (
        f"MECE violation: concerns implemented by BOTH layers: {sorted(overlap)}. "
        f"Split into two distinct concerns or move to a single owner."
    )


def test_collectively_exhaustive():
    all_impls = PREDICATE_CHECK_IDS | _rubric_concern_ids()
    missing = CONCERNS_BY_ID.keys() - all_impls
    assert not missing, (
        f"concerns declared but not implemented anywhere: {sorted(missing)}. "
        f"Add a predicate or rubric criterion, or remove the concern."
    )


def test_owner_consistency_deterministic():
    for check_id in PREDICATE_CHECK_IDS:
        concern = CONCERNS_BY_ID.get(check_id)
        if concern is None:
            continue
        assert concern.owner == Owner.DETERMINISTIC, (
            f"predicate emits {check_id} but concern is owned by {concern.owner.value}"
        )


def test_owner_consistency_rubric():
    for concern_id in _rubric_concern_ids():
        concern = CONCERNS_BY_ID.get(concern_id)
        if concern is None:
            continue
        assert concern.owner == Owner.RUBRIC, (
            f"rubric criterion implements {concern_id} but concern is owned by {concern.owner.value}"
        )


@pytest.mark.parametrize("concern", CONCERNS, ids=lambda c: c.id)
def test_every_concern_has_description(concern):
    assert concern.description.strip(), f"concern {concern.id} has empty description"
