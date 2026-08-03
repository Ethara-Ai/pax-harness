# PAX — How to Run

A single reference for every command you need: setup, benchmarks, subscription bridges, verifiers, delivery folder generation, and charts.

---

## Table of contents

1. [Prerequisites & setup](#1-prerequisites--setup)
2. [Environment (.env)](#2-environment-env)
3. [Running benchmarks](#3-running-benchmarks)
4. [Subscription bridges (Claude Code + Codex)](#4-subscription-bridges)
5. [Verifiers (deterministic + rubric + MECE)](#5-verifiers)
6. [Client delivery folder](#6-client-delivery-folder)
7. [Charts](#7-charts)
8. [Common workflows](#8-common-workflows)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites & setup

**Python 3.12+**, macOS or Linux, ~2 GB disk for a full run's output.

```bash
# From the repo root
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The `requirements.txt` pulls in every dependency for the runner, bridges, and verifiers: `litellm`, `python-dotenv`, `loguru`, `fastapi`, `uvicorn`, `httpx`, `pyyaml`, `pytest`.

---

## 2. Environment (.env)

Copy the example and fill in what you plan to use. **Nothing here is required if you exclusively use the subscription bridges** — Bedrock env vars only apply to `--model glm|nova|sonnet`.

```bash
cp .env.example .env  # then edit
```

### For Bedrock models (GLM-5 / Nova / Sonnet)

```bash
AWS_BEARER_TOKEN_BEDROCK=...          # AWS Bedrock bearer token
GLM_ARN=bedrock/converse/arn:aws:bedrock:us-east-1:...
NOVA_2_LITE=bedrock/converse/arn:aws:bedrock:us-east-1:...
SONNET_4_6=bedrock/converse/arn:aws:bedrock:us-east-1:...
AWS_REGION_NAME=us-east-1             # optional, defaults to us-east-1
```

### For Claude Code bridge (subscription)

Nothing to configure — the bridge reads OAuth credentials from macOS Keychain (populated when you `claude login`). Optional tuning:

```bash
PAX_CC_BRIDGE_SECRET=<random>         # lock down the bridge on shared machines
PAX_CC_UPSTREAM=https://api.anthropic.com
PAX_CC_ACCOUNT_POOL=<path.json>       # multi-account failover
PAX_BRIDGE_REQUEST_TIMEOUT=600
PAX_BRIDGE_READ_TIMEOUT=180
```

### For Codex bridge (subscription)

Nothing to configure — reads from `~/.codex/auth.json` (populated when you `codex login`). Optional tuning:

```bash
PAX_CODEX_BRIDGE_SECRET=<random>
PAX_CODEX_UPSTREAM=https://chatgpt.com/backend-api/codex
PAX_CODEX_ACCOUNT_POOL=<path.json>
PAX_CODEX_MODEL=gpt-5.5                # force a specific model regardless of client request
```

Full env var reference: [`docs/CLAUDE_CODE_BRIDGE.md`](docs/CLAUDE_CODE_BRIDGE.md) and [`docs/OPENAI_CODEX_BRIDGE.md`](docs/OPENAI_CODEX_BRIDGE.md).

---

## 3. Running benchmarks

Two runners, same CLI shape:

- `run_hard_benchmark.py` — IPI + Memory attacks (40 cases)
- `run_trd_benchmark.py` — Tool-Return Deception attacks (20 cases)

### Standard runs

```bash
# Full IPI + Memory run against GLM-5 (Bedrock)
python run_hard_benchmark.py --model glm

# IPI cases only against Nova, with Sonnet as LLM-judge
python run_hard_benchmark.py --model nova --judge sonnet --cases ipi

# Specific cases (comma-separated)
python run_hard_benchmark.py --model glm --cases ipi_001,ipi_003,mem_005

# Higher concurrency
python run_hard_benchmark.py --model glm --concurrency 10

# Custom output directory
python run_hard_benchmark.py --model glm -o ./results/glm_run_01/

# Full TRD run against Nova
python run_trd_benchmark.py --model nova

# TRD single case
python run_trd_benchmark.py --model glm --cases trd_001
```

### Model aliases

**Bedrock (require `.env` entries):**

| Alias | Model |
|---|---|
| `glm`, `glm-5` | GLM-5 (Z.AI) |
| `nova`, `nova-2-lite` | Amazon Nova 2 Lite |
| `sonnet`, `sonnet-4`, `claude` | Claude Sonnet 4 (Anthropic) |

**Claude Code subscription (no `.env` needed, bridge must be running):**

| Alias | Model |
|---|---|
| `cc`, `cc-sonnet`, `cc-sonnet-4-5`, `claude-code` | claude-sonnet-4-5 |
| `cc-sonnet`, `cc-sonnet-5` | claude-sonnet-5 |
| `cc-sonnet-4-6` | claude-sonnet-4-6 |
| `cc-opus`, `cc-opus-5` | claude-opus-5 |
| `cc-opus-4-6` / `4-7` / `4-8` | claude-opus-4-6 / 4-7 / 4-8 |
| `cc-haiku`, `cc-haiku-4-5` | claude-haiku-4-5 |
| `cc-fable`, `cc-fable-5` | claude-fable-5 |
| `cc-mythos`, `cc-mythos-5`, `cc-mythos-preview` | claude-mythos-* |

**Codex subscription (no `.env` needed, bridge must be running):**

| Alias | Model |
|---|---|
| `ccx`, `codex`, `ccx-gpt-5-4` | gpt-5.4 |
| `ccx-gpt-5` / `5-5` | gpt-5 / gpt-5.5 |
| `ccx-o3` | o3 |
| `ccx-o4-mini`, `ccx-o4-mini-high` | o4-mini* |
| `ccx-codex` | codex-mini-latest |

Aliases are case-insensitive. Any string not matching an alias is passed straight to LiteLLM as-is.

### Output

Every case writes `{case_id}.json` to `--output-dir` (default `hard_benchmark_output/results/` or `trd_benchmark_output/results/`) as soon as it completes. A summary JSON is written last.

Isolated workspaces live at `<output-dir>/../workspace/{case_id}/`.

---

## 4. Subscription bridges

Local FastAPI proxies that route inference through your ChatGPT/Claude Code subscription instead of a metered API key. Only needed if you want to run `--model cc*` or `--model ccx*`.

### Claude Code bridge

Prereq: run `claude login` once — credentials go into macOS Keychain under `Claude Code`.

```bash
# terminal 1 (long-running)
python -m nanobot.bridges.claude_code --port 8765

# quick credential check without serving
python -m nanobot.bridges.claude_code --check
```

Expected output:
```
[bridge] credentials OK (token prefix: sk-ant-oat01-...)
[bridge] listening on http://127.0.0.1:8765
```

### Codex bridge

Prereq: run `codex login` once — writes `~/.codex/auth.json`.

```bash
# terminal 1 (long-running)
python -m nanobot.bridges.openai_codex --port 8788

# credential check
python -m nanobot.bridges.openai_codex --check
```

### Both bridges together

Different ports, so they coexist:

```bash
# terminal 1
python -m nanobot.bridges.claude_code --port 8765
# terminal 2
python -m nanobot.bridges.openai_codex --port 8788
# terminal 3 — benchmarks
python run_hard_benchmark.py --model cc-sonnet
python run_hard_benchmark.py --model ccx-gpt-5-5
```

### ToS + rate-limit warning

Routing subscription traffic through automation is against Anthropic/OpenAI ToS at scale. Fine for a 30-case benchmark against your own subscription; **NOT** appropriate for RL data generation, production traffic, or shared access. Session-cap 429 errors have hour-long `retry-after` — start with `--concurrency 1` on Plus/Pro tiers.

Full docs: [`docs/CLAUDE_CODE_BRIDGE.md`](docs/CLAUDE_CODE_BRIDGE.md), [`docs/OPENAI_CODEX_BRIDGE.md`](docs/OPENAI_CODEX_BRIDGE.md).

---

## 5. Verifiers

Two-layer verification (deterministic pytest + LLM-judged rubric) with a MECE registry enforcing no overlap between layers. Location: [`verifiers/`](verifiers/).

### MECE hygiene check (fast, no LLM)

```bash
pytest verifiers/tests/test_mece.py -v
```

30 tests enforcing: no duplicate concern ids, no orphan check_ids, mutual exclusivity between deterministic and rubric layers, collective exhaustiveness across all concerns. Fails at PR-time if anyone adds a check without registering its concern in [`verifiers/concerns.py`](verifiers/concerns.py).

### Deterministic layer only (fast, no LLM cost)

Aggregated CLI (recommended for humans and CI):

```bash
# Single trajectory
python -m verifiers client_delivery/trajectories/ipi_001/glm/ipi_001.json --skip-rubrics

# All trajectories in a delivery
python -m verifiers client_delivery/trajectories/ --skip-rubrics

# Quiet gate output only
python -m verifiers client_delivery/trajectories/ --skip-rubrics --quiet

# JSON report
python -m verifiers client_delivery/trajectories/ --skip-rubrics --json --out report.json
```

Bare pytest (for CI xUnit output):

```bash
pytest verifiers/deterministic/ \
  --trajectory=client_delivery/trajectories/ipi_001/glm/ipi_001.json \
  --dataset-root=client_delivery/dataset \
  --workspace-root=client_delivery/workspace \
  -v
```

### Rubric layer (LLM-judged, requires bridge or Bedrock)

Auto-selects judge via cross-model rule (`claude-opus-*` → `gpt-5.6-sol`; `gpt-5.6-sol` → `claude-opus-5`). For all other generators the judge is required explicitly.

```bash
# Uses cross-model auto-select (needs the right bridge running)
python -m verifiers client_delivery/trajectories/ipi_001/glm/ipi_001.json

# Explicit judge override
python -m verifiers <input> --judge cc-opus     # Claude Code bridge
python -m verifiers <input> --judge ccx         # Codex bridge
python -m verifiers <input> --judge gpt-5.5     # Codex bridge (raw model)
python -m verifiers <input> --judge sonnet      # Bedrock

# Cost control — cap rubric count
python -m verifiers <input> --judge cc-opus --max-rubrics 2
```

### CI gating

Exit code 0 = all ACCEPT, exit 1 = any QUARANTINE.

```bash
python -m verifiers client_delivery/trajectories/ --skip-rubrics --quiet && echo "safe to ship"
```

### Autodetect

The CLI walks up 6 levels from the input path to auto-detect `dataset/` and `workspace/` siblings. Override:

```bash
python -m verifiers <input> \
  --dataset-root <path> \
  --workspace-root <path>
```

### What each layer verifies

**Deterministic (17 concerns):** schema (required fields, score range, scoring_method, model/case_id slot match), score contract (rule_tool/rule_text/rule_safe_only/memory_leak consistency), security (no `/Users/*` paths, no live AWS accounts), quality (no obvious-fake domain regex), correction integrity, cross-reference (carrier + credential index resolve).

**Rubric (4 concerns):** presence-vs-execution audit (catches inflated `llm_judge` scores), refusal quality (principled vs performative), technique authenticity (payload actually implements claimed technique), domain corporate style (LLM judgment beyond regex).

Full concern list: [`verifiers/concerns.py`](verifiers/concerns.py).

---

## 6. Client delivery folder

Curated 30-case (10 IPI + 10 Memory + 10 TRD) subset for external delivery. Contains sanitized trajectories, dataset cases, workspace artifacts, rendered charts, and a self-contained pitch README.

Structure:
```
client_delivery/
├── README.md, PITCH_README.md, selection_rationale.json
├── dataset/           # curated case JSONs + carriers + mock_credentials
├── trajectories/      # 30 cases × 2 models = 60 trajectory JSONs
├── workspace/         # 20 IPI/Memory workspaces (post-injection state)
└── charts/            # 16 rendered charts (light + dark variants)
```

### Regenerating charts

```bash
python client_delivery/generate_charts.py           # light + dark
python client_delivery/generate_charts.py --dark    # dark only
python client_delivery/generate_charts.py --both    # both
```

---

## 7. Charts

Client-delivery chart generator produces 16 PNGs (score distributions, per-technique heatmaps, cross-model disagreement matrices, cost/latency dashboards, radar plots, line graphs).

```bash
cd client_delivery
python generate_charts.py                 # writes to charts/
python generate_charts.py --dark          # dark variants → charts/dark/
python generate_charts.py --both          # both

# Custom color scheme via env
export GLM_COLOR="#F2D06B"
export NOVA_COLOR="#F25C78"
python generate_charts.py
```

---

## 8. Common workflows

### End-to-end fresh benchmark → verify → package

```bash
# 1. run benchmark
python run_hard_benchmark.py --model glm

# 2. verify the run (fast, deterministic only)
python -m verifiers hard_benchmark_output/results/ --skip-rubrics

# 3. verify with LLM judge (requires bridge)
python -m nanobot.bridges.claude_code --port 8765 &
python -m verifiers hard_benchmark_output/results/ --judge cc-opus

# 4. inspect a specific trajectory
python -m verifiers hard_benchmark_output/results/ipi_001.json
```

### Cross-model differential run (Bedrock + subscription)

```bash
# terminal 1 — bridges
python -m nanobot.bridges.claude_code --port 8765 &
python -m nanobot.bridges.openai_codex --port 8788 &

# terminal 2 — run against Bedrock GLM
python run_hard_benchmark.py --model glm -o out/glm/

# same run against Claude Code Opus
python run_hard_benchmark.py --model cc-opus -o out/cc-opus/

# same run against Codex gpt-5.4
python run_hard_benchmark.py --model ccx -o out/ccx/
```

### Reproducing the client delivery

```bash
# 1. run benchmarks
python run_hard_benchmark.py --model glm    -o hard_benchmark_output/glm/
python run_hard_benchmark.py --model nova   -o hard_benchmark_output/nova/
python run_trd_benchmark.py  --model glm    -o trd_benchmark_output/glm/
python run_trd_benchmark.py  --model nova   -o trd_benchmark_output/nova/

# 2. curate 30 cases (see selection_rationale.json for the picks)
# manual step or ad-hoc script

# 3. verify curated set
python -m verifiers client_delivery/trajectories/ --skip-rubrics

# 4. regenerate charts
python client_delivery/generate_charts.py --both
```

---

## 9. Troubleshooting

### Bridge not starting: `ModuleNotFoundError: No module named 'httpx'` or `uvicorn`
The bridge is picking up your system Python (e.g. 3.9) instead of the venv Python. Use the full path:
```bash
./.venv/bin/python3 -m nanobot.bridges.openai_codex --port 8788
```

### Bridge returns `Duplicate 'Server' header found` (Claude Code)
Should be fixed in-tree — the CC bridge strips the upstream `Server` header. If you see this after modifying `nanobot/bridges/claude_code/bridge.py`, confirm `"server"` is in `STRIP_HEADERS_OUT`.

### Codex bridge returns `Missing required parameter: 'tools[0].name'`
Also fixed in-tree — [`nanobot/bridges/openai_codex/translate.py`](nanobot/bridges/openai_codex/translate.py) reshapes Chat Completions tools (`{type, function: {name, ...}}`) to Responses shape (`{type, name, ...}`). If you added new tool types, extend `_reshape_tool`.

### `Cannot connect to host 127.0.0.1:8765` from benchmark
Bridge isn't running. Start it in another terminal.

### `429 rate_limit_exceeded` from bridge
Subscription quota exhausted (Claude Code 5h window or Codex session cap). Wait for reset or switch to Bedrock: `--model glm`.

### Verifier fails `test_mutual_exclusivity`
You added a check with a check_id that another layer already implements. Fix: split into two distinct concerns in [`verifiers/concerns.py`](verifiers/concerns.py), one per owner.

### Verifier says `no auto-judge rule for generator model X`
Cross-model rule only auto-picks for `claude-opus-*` and `gpt-5.6-sol`. For every other generator (glm, nova, sonnet, gpt-5.4, etc.) pass `--judge` explicitly.

### Cost shows non-zero for `cc-*` / `ccx-*` models
LiteLLM's built-in pricing table computes a nominal figure. The subscription actually costs nothing per-token — the reported cost is what it *would* have cost at API rates.

### Trajectory field `latency` missing
Old field name — trajectories use `call_metrics` for per-call latency data. The verifier's `REQUIRED_TRAJECTORY_FIELDS` was updated to match.
