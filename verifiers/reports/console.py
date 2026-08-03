from __future__ import annotations

import sys

from verifiers.schemas import CheckStatus, Gate, VerificationReport


STATUS_SYMBOL = {
    CheckStatus.PASS: "PASS",
    CheckStatus.FAIL: "FAIL",
    CheckStatus.SKIP: "SKIP",
    CheckStatus.ERROR: "ERR ",
}

GATE_SYMBOL = {Gate.ACCEPT: "ACCEPT", Gate.QUARANTINE: "QUARANTINE"}


def print_report(report: VerificationReport, verbose: bool = True, stream=sys.stdout) -> None:
    print(f"\n=== {report.case_id} / {report.model} ({report.trajectory_path}) ===", file=stream)
    print(f"    recorded_score: {report.recorded_score}   gate: {GATE_SYMBOL[report.gate]}   "
          f"judge: {report.judge_model or '(none)'}   duration: {report.duration_seconds:.2f}s", file=stream)
    print(f"    checks: {report.passed} pass / {report.failed} fail / {report.skipped} skip / "
          f"{report.errored} error  (of {len(report.checks)})", file=stream)
    if verbose:
        for check in report.checks:
            if check.status == CheckStatus.SKIP:
                continue
            evidence = check.evidence or check.reasoning
            print(f"      {STATUS_SYMBOL[check.status]}  [{check.tier:<8}] "
                  f"{check.id:<40} {evidence}", file=stream)
    if report.findings:
        print("    findings:", file=stream)
        for finding in report.findings:
            print(f"      - {finding}", file=stream)


def print_summary(reports: list[VerificationReport], stream=sys.stdout) -> None:
    total = len(reports)
    accepted = sum(1 for r in reports if r.gate == Gate.ACCEPT)
    quarantined = total - accepted
    total_checks = sum(len(r.checks) for r in reports)
    total_failed = sum(r.failed for r in reports)
    total_errored = sum(r.errored for r in reports)
    print("\n" + "=" * 72, file=stream)
    print(f"VERIFICATION SUMMARY: {total} trajectories", file=stream)
    print(f"  gate: {accepted} ACCEPT / {quarantined} QUARANTINE", file=stream)
    print(f"  checks: {total_checks - total_failed - total_errored} pass / "
          f"{total_failed} fail / {total_errored} error", file=stream)
    if quarantined:
        print("  quarantined trajectories:", file=stream)
        for r in reports:
            if r.gate == Gate.QUARANTINE:
                print(f"    - {r.case_id} / {r.model}   ({r.trajectory_path})", file=stream)
    print("=" * 72, file=stream)
