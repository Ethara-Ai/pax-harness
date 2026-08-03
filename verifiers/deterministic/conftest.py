from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--trajectory", action="store", default=None,
                     help="Path to a trajectory JSON to verify")
    parser.addoption("--dataset-root", action="store", default=None,
                     help="Path to the dataset root (contains ipi_cases/, memory_cases/, trd_cases/)")
    parser.addoption("--workspace-root", action="store", default=None,
                     help="Path to the workspace/ root for carrier resolution")


def _resolve(opt: str, env: str, config) -> str | None:
    return config.getoption(opt) or os.environ.get(env)


@pytest.fixture(scope="session")
def trajectory_path(request) -> Path:
    p = _resolve("--trajectory", "PAX_VERIFIER_TRAJECTORY", request.config)
    if not p:
        pytest.skip("no --trajectory or PAX_VERIFIER_TRAJECTORY provided")
    return Path(p)


@pytest.fixture(scope="session")
def trajectory(trajectory_path: Path) -> dict:
    with open(trajectory_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def dataset_root(request) -> Path | None:
    p = _resolve("--dataset-root", "PAX_VERIFIER_DATASET", request.config)
    return Path(p) if p else None


@pytest.fixture(scope="session")
def workspace_root(request) -> Path | None:
    p = _resolve("--workspace-root", "PAX_VERIFIER_WORKSPACE", request.config)
    return Path(p) if p else None


@pytest.fixture(scope="session")
def dataset_case(trajectory: dict, dataset_root: Path | None) -> dict | None:
    if dataset_root is None:
        return None
    case_id = trajectory.get("case_id", "")
    prefix = case_id.split("_", 1)[0]
    subdirs = {"ipi": "ipi_cases", "mem": "memory_cases", "trd": "trd_cases"}
    subdir = subdirs.get(prefix)
    if subdir is None:
        return None
    idx = case_id.split("_", 1)[1] if "_" in case_id else ""
    for candidate in (dataset_root / subdir / f"case_{idx}.json",
                      dataset_root / subdir / f"{case_id}.json"):
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
    return None


@pytest.fixture(scope="session")
def expected_case_id(trajectory_path: Path) -> str:
    return trajectory_path.stem


@pytest.fixture(scope="session")
def expected_model(trajectory_path: Path) -> str | None:
    slot = trajectory_path.parent.name
    return {"glm": "glm-5", "nova": "nova-2-lite"}.get(slot)
