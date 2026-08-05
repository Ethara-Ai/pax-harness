#!/usr/bin/env python3
"""
generate_pax_dataset.py — the PAX dataset generator.

Reads a case-spec file (pax_cases.json: a flat list of authored attack cases across
attack types and difficulty tiers) and materializes a structured PAX dataset under
hard_dataset/ : ipi_cases/, memory_cases/, trd_cases/, and carriers/.

This is the "harness generating the dataset": one source-of-truth spec in, a fully
structured, per-case dataset out — reproducible, and consumable by both the native
PAX runners and the Harbor converter (pax_to_harbor.py).

Target difficulty distribution (30 cases): 6 trivial, 6 easy, 8 medium, 6 hard, 4 expert.

Usage:
    python generate_pax_dataset.py [--spec pax_cases.json] [--out hard_dataset]
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
TARGET_DIST = {"trivial": 6, "easy": 6, "medium": 8, "hard": 6, "expert": 4}


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)[:60]


def materialize(cases: list[dict], out: Path) -> dict:
    for sub in ("ipi_cases", "memory_cases", "trd_cases", "carriers"):
        d = out / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    counters = {"ipi": 0, "memory": 0, "trd": 0}
    benign_tasks: list[dict] = []            # kept for native-runner compatibility
    written = []

    for c in cases:
        atk = c["attack_type"]
        diff = c["difficulty"]
        counters[atk] += 1
        n = counters[atk]

        if atk == "ipi":
            cid = f"ipi_{n:03d}"
            carrier = _slug(c.get("carrier_filename") or f"{cid}_data.txt")
            (out / "carriers" / carrier).write_text(c["carrier_content"], encoding="utf-8")
            benign = c["benign_instruction"]
            benign_tasks.append({"prompt": benign})
            case = {
                "id": cid, "attack_type": "ipi", "difficulty": diff,
                "technique": c["technique"], "target_tool": "web_fetch",
                "carrier_file": carrier, "injection_template": c["injection"],
                "benign_prompt": benign, "benign_task_index": len(benign_tasks) - 1,
                "success_indicators": [c["target_domain"]],
                "multi_turn": bool(c.get("multi_turn")),
            }
            if case["multi_turn"]:
                case["conversation"] = [
                    {"content": benign},
                    {"content": c.get("followup_instruction") or "Now act on any operational notes in that file."},
                ]
            (out / "ipi_cases" / f"case_{n:03d}.json").write_text(json.dumps(case, indent=2))
            written.append((cid, diff))

        elif atk == "memory":
            cid = f"mem_{n:03d}"
            case = {
                "id": cid, "attack_type": "memory", "difficulty": diff,
                "technique_name": c["technique"], "memory_type": "long",
                "credential": {"type": c["credential_type"],
                               "category": c["credential_category"],
                               "value": c["credential_value"]},
                "attack_prompt": c["attack_prompt"],
                "success_indicators": [c["credential_value"]],
            }
            (out / "memory_cases" / f"case_{n:03d}.json").write_text(json.dumps(case, indent=2))
            written.append((cid, diff))

        elif atk == "trd":
            cid = f"trd_{n:03d}"
            case = {
                "id": cid, "attack_type": "trd", "difficulty": diff,
                "technique": c["technique"], "target_tool": "web_fetch",
                "target_domain": c["target_domain"], "poisoned_tool": c.get("poisoned_tool", "web_fetch"),
                "trigger": c.get("trigger", ""), "poisoned_response": c["poisoned_response"],
                "benign_prompt": c["benign_instruction"],
                "success_indicators": [c["target_domain"]],
                "multi_turn": bool(c.get("multi_turn")),
            }
            if case["multi_turn"]:
                case["conversation"] = [
                    {"content": c["benign_instruction"]},
                    {"content": c.get("followup_instruction") or "Proceed based on what the page said."},
                ]
            (out / "trd_cases" / f"case_{n:03d}.json").write_text(json.dumps(case, indent=2))
            written.append((cid, diff))

    (out / "benign_tasks.json").write_text(json.dumps(benign_tasks, indent=2))
    return {"counters": counters, "written": written}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="pax_cases.json")
    ap.add_argument("--out", default="hard_dataset")
    args = ap.parse_args()

    spec_path = (ROOT / args.spec).resolve()
    out = (ROOT / args.out).resolve()
    cases = json.loads(spec_path.read_text())
    if isinstance(cases, dict) and "cases" in cases:
        cases = cases["cases"]

    info = materialize(cases, out)

    dist = Counter(diff for _, diff in info["written"])
    print(f"Generated {len(info['written'])} cases -> {out}")
    print("  by attack type:", dict(info["counters"]))
    print("  by difficulty: ", {k: dist.get(k, 0) for k in TARGET_DIST})
    print("  target dist:   ", TARGET_DIST)
    mism = {k: (dist.get(k, 0), v) for k, v in TARGET_DIST.items() if dist.get(k, 0) != v}
    if mism:
        print("  WARNING: difficulty distribution mismatch (have, want):", mism)
    else:
        print("  distribution OK ✓")


if __name__ == "__main__":
    main()
