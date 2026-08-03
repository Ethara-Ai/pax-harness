from __future__ import annotations

import argparse
import sys
from pathlib import Path

from verifiers.evaluator import EvaluatorOptions, verify_trajectory
from verifiers.reports.console import print_report, print_summary
from verifiers.reports.json import dumps as reports_dumps
from verifiers.schemas import Gate
from verifiers.verifier_loop import find_trajectory_files


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m verifiers",
                                description="Verify PAX trajectories (deterministic + rubric layers).")
    p.add_argument("input", help="Trajectory JSON file OR directory containing trajectory JSONs")
    p.add_argument("--dataset-root", type=Path, default=None,
                   help="Path to dataset root (contains ipi_cases/, memory_cases/, trd_cases/). "
                        "Auto-detected as <input>/../dataset if omitted.")
    p.add_argument("--workspace-root", type=Path, default=None,
                   help="Path to workspace/ root for carrier resolution. "
                        "Auto-detected as <input>/../workspace if omitted.")
    p.add_argument("--judge", type=str, default=None,
                   help="LLM judge model. Omit to auto-select via cross-model rule "
                        "(claude-opus-* -> gpt-5.6-sol; gpt-5.6-sol -> claude-opus-5).")
    p.add_argument("--skip-rubrics", action="store_true",
                   help="Skip LLM-judged rubric layer (deterministic only, no LLM cost).")
    p.add_argument("--skip-deterministic", action="store_true",
                   help="Skip deterministic pytest layer (rubrics only).")
    p.add_argument("--max-rubrics", type=int, default=None,
                   help="Cap number of rubric criteria evaluated (for cost control).")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    p.add_argument("--quiet", action="store_true", help="Print gate summary line only.")
    p.add_argument("--out", type=Path, default=None, help="Write JSON report to file.")
    return p


def _autodetect_roots(input_path: Path, args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    dataset_root = args.dataset_root
    workspace_root = args.workspace_root
    base = input_path.parent if input_path.is_file() else input_path
    for candidate in [base, *base.parents][:6]:
        if dataset_root is None and (candidate / "dataset").is_dir():
            dataset_root = candidate / "dataset"
        if workspace_root is None and (candidate / "workspace").is_dir():
            workspace_root = candidate / "workspace"
        if dataset_root is not None and workspace_root is not None:
            break
    return dataset_root, workspace_root


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: {input_path} does not exist", file=sys.stderr)
        return 2

    dataset_root, workspace_root = _autodetect_roots(input_path, args)

    options = EvaluatorOptions(
        dataset_root=dataset_root,
        workspace_root=workspace_root,
        skip_rubrics=args.skip_rubrics,
        skip_deterministic=args.skip_deterministic,
        judge_override=args.judge,
        judge_max_rubrics=args.max_rubrics,
    )

    files = find_trajectory_files(input_path)
    if not files:
        print(f"error: no trajectory JSONs found under {input_path}", file=sys.stderr)
        return 2

    reports = [verify_trajectory(f, options) for f in files]

    if args.out is not None:
        args.out.write_text(reports_dumps(reports))

    if args.json:
        print(reports_dumps(reports))
    elif args.quiet:
        for r in reports:
            print(f"{r.gate.value:<10} {r.case_id}/{r.model}   score={r.recorded_score}")
    else:
        for r in reports:
            print_report(r)
        if len(reports) > 1:
            print_summary(reports)

    return 0 if all(r.gate == Gate.ACCEPT for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
