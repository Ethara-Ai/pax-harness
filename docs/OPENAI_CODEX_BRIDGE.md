# OpenAI Codex / ChatGPT Subscription Bridge

Route PAX benchmark inference through your local ChatGPT/Codex OAuth subscription instead of the OpenAI API. Useful when you have a ChatGPT Plus/Pro subscription and want to avoid API-key spend for evaluation runs.

The bridge lives at `nanobot/bridges/openai_codex/`. It exposes an OpenAI-compatible endpoint on `127.0.0.1:8788`, reads your ChatGPT OAuth credentials from the local Codex config, forwards requests upstream, and translates between Chat Completions and Responses API as needed (`translate.py`).

## Prerequisites

1. **Codex CLI** installed and authenticated on this machine — credentials live under `~/.codex/auth.json` (or your platform's Codex config path).
2. **Python 3.12+** with PAX dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Start the bridge (terminal 1, long-running)

```bash
python -m nanobot.bridges.openai_codex --port 8788
```

Expected output:
```
[pax-codex] credentials OK (token prefix: eyJhbGciOi..., account: 01234567...)
[pax-codex] listening on http://127.0.0.1:8788
[pax-codex] point clients at:
           export OPENAI_BASE_URL=http://127.0.0.1:8788
           export OPENAI_API_KEY=$PAX_CODEX_BRIDGE_SECRET   # (or a stub)
```

Pre-flight check without serving:
```bash
python -m nanobot.bridges.openai_codex --check
```

### 2. Run the benchmark (terminal 2)

```bash
python run_hard_benchmark.py --model ccx
```

The runner detects the Codex-family model prefix (`gpt-*`, `o1`, `o3`, `o4-*`, `codex-*`), points LiteLLM at the local bridge, and forwards all traffic through your subscription.

### 3. Model aliases

Aliases prefixed `ccx-` map directly to Codex models (no environment variable required):

| Alias | Model ID |
|---|---|
| `ccx`, `codex`, `ccx-gpt-5-4` | `gpt-5.4` (default) |
| `ccx-gpt-5` | `gpt-5` |
| `ccx-gpt-5-5` | `gpt-5.5` |
| `ccx-o3` | `o3` |
| `ccx-o4-mini` | `o4-mini` |
| `ccx-o4-mini-high` | `o4-mini-high` |
| `ccx-codex` | `codex-mini-latest` |

Your subscription tier (Plus vs Pro vs Team) determines which models actually respond.

You can also pass a full model ID directly:
```bash
python run_hard_benchmark.py --model gpt-5.5
python run_hard_benchmark.py --model o3
```

## Environment variables

All are optional — sensible defaults are baked in.

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_BASE_URL` | `http://127.0.0.1:8788` | Where the runner sends Codex requests |
| `OPENAI_API_KEY` | `pax-ccx-stub` | Placeholder (bridge accepts any non-empty value) |
| `PAX_CODEX_UPSTREAM` | `https://chatgpt.com/backend-api/codex` | Upstream that the bridge forwards to |
| `PAX_CODEX_MAX_INLINE_RETRIES` | (unset) | Bridge-side transient-error retries |
| `PAX_CODEX_MAX_INLINE_WAIT` | (unset) | Max seconds bridge will pause inline |
| `PAX_BRIDGE_REQUEST_TIMEOUT` | `600` | Non-stream request timeout (seconds) |
| `PAX_BRIDGE_READ_TIMEOUT` | `180` | Non-stream per-chunk read timeout |
| `PAX_BRIDGE_STREAM_READ_TIMEOUT` | `600` | Streaming per-chunk read timeout |
| `PAX_BRIDGE_CONNECT_TIMEOUT` | `30` | TCP connect timeout |
| `PAX_CODEX_ACCOUNT_POOL` | (unset) | Path to JSON pool for multi-account failover |
| `PAX_CODEX_BRIDGE_SECRET` | (unset) | If set, clients must present it via `Authorization: Bearer` or `x-pax-bridge-secret`. Without it the bridge is unauthenticated on localhost. |

## Rate limits and quota

The bridge uses your **ChatGPT/Codex subscription session quota**, not per-token API pricing. Plus/Pro tiers each have overlapping limits:

- Per-minute request rate
- Rolling message/session quotas
- Per-model daily caps (e.g. GPT-5.5 and o-series have separate weekly caps)

A single PAX benchmark run at `--concurrency 5` with multi-turn IPI cases can burst 300+ LLM calls in ~2 minutes and exhaust a session window. The runner does not cap concurrency for you.

**Rule of thumb:** for the full 30-case delivery, `--concurrency 5` completes in a few minutes and stays comfortably under Pro quotas. Plus subscribers should start with `--concurrency 1` and scale up. Do not use the bridge for RL data generation or 10K+ episode runs — that is against OpenAI ToS and will lock your subscription.

Cost tracking reports `$0.00` for Codex models — token usage is still recorded in trajectory JSONs for accounting purposes.

## Running both bridges simultaneously

The Claude Code bridge listens on `8765` and the Codex bridge on `8788`, so they coexist. In a three-terminal setup:

```bash
# terminal 1
python -m nanobot.bridges.claude_code --port 8765
# terminal 2
python -m nanobot.bridges.openai_codex --port 8788
# terminal 3 — run against Claude via CC
python run_hard_benchmark.py --model cc
# then run against Codex
python run_hard_benchmark.py --model ccx
```

The runner picks the right bridge automatically from the resolved model ID.

## Troubleshooting

**`credentials error: no Codex credentials found`**
Log in via the Codex CLI first. Confirm `~/.codex/auth.json` exists and contains a `tokens.access_token`.

**`connection refused` from benchmark**
The bridge is not running. Start it in terminal 1: `python -m nanobot.bridges.openai_codex --port 8788`.

**`429` or session-cap errors**
Subscription quota exhausted. Wait for the reset window or switch to Bedrock: `--model glm`.

**Different port**
Both sides must agree. Start bridge with `--port 9001` and export `OPENAI_BASE_URL=http://127.0.0.1:9001`.

**Chat Completions vs Responses API**
The bridge exposes both. LiteLLM's `openai/` route uses Chat Completions by default; the bridge's `translate.py` handles conversion to/from the Codex Responses API upstream. No client-side configuration needed.

## Terms of service

Routing subscription-authenticated traffic through automated tooling is against OpenAI's ToS at scale. This bridge is intended for individual research and evaluation — running 30 benchmark cases against your own subscription. Do not use it to serve production traffic, generate training data at scale, or share subscription access.
