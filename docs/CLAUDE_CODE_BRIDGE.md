# Claude Code Subscription Bridge

Route PAX benchmark inference through your local Claude Code OAuth subscription instead of the Anthropic API. Useful when you have a Pro/Max subscription and want to avoid API-key spend for evaluation runs.

The bridge lives at `nanobot/bridges/claude_code/`. It exposes an Anthropic-compatible `/v1/messages` endpoint on `127.0.0.1:8765`, reads your OAuth credentials from macOS Keychain, and forwards requests upstream with the required OAuth bearer token, `anthropic-beta: oauth-2025-04-20` header, and `You are Claude Code` system prefix.

## Prerequisites

1. **Claude Code** installed and authenticated on this machine (`claude login` — credentials must exist in macOS Keychain under the `Claude Code` service).
2. **Python 3.12+** with PAX dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Start the bridge (terminal 1, long-running)

```bash
python -m nanobot.bridges.claude_code --port 8765
```

Expected output:
```
[bridge] credentials OK (token prefix: sk-ant-oat01-...)
[bridge] listening on http://127.0.0.1:8765
[bridge] point clients at:
           export ANTHROPIC_API_BASE=http://127.0.0.1:8765
           export ANTHROPIC_API_KEY=pax-cc-stub
```

Pre-flight check without serving:
```bash
python -m nanobot.bridges.claude_code --check
```

### 2. Run the benchmark (terminal 2)

```bash
python run_hard_benchmark.py --model cc
```

The runner detects the `claude-*` model, points LiteLLM at the local bridge, and forwards all traffic through your subscription.

### 3. Model aliases

Aliases prefixed `cc-` map directly to Claude Code models (no environment variable required):

| Alias | Model ID |
|---|---|
| `cc`, `claude-code` | `claude-sonnet-4-5` (stable default) |
| `cc-sonnet`, `cc-sonnet-5` | `claude-sonnet-5` (latest Sonnet) |
| `cc-sonnet-4-6` / `cc-sonnet-4-5` | Older Sonnet variants |
| `cc-opus`, `cc-opus-5` | `claude-opus-5` (recommended flagship for agentic work) |
| `cc-opus-4-8` / `cc-opus-4-7` / `cc-opus-4-6` | Older Opus variants |
| `cc-haiku`, `cc-haiku-4-5` | `claude-haiku-4-5` (fast/cheap) |
| `cc-haiku-4-5-20251001` | Date-pinned Haiku 4.5 |
| `cc-fable`, `cc-fable-5` | `claude-fable-5` (most capable widely available) |
| `cc-mythos`, `cc-mythos-5` | `claude-mythos-5` (Project Glasswing, invitation-only) |
| `cc-mythos-preview` | `claude-mythos-preview` (invitation-only) |

Your subscription tier (Pro vs Max) determines which models actually respond. Fable 5 / Mythos 5 require the appropriate tier or Glasswing access. `sonnet`, `claude`, and `sonnet-4` (no `cc-` prefix) remain bound to `SONNET_4_6` Bedrock ARN — the CC bridge does not shadow existing behavior.

You can also pass a full model ID directly:
```bash
python run_hard_benchmark.py --model claude-opus-4-8
```

## Environment variables

All are optional — sensible defaults are baked in.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_BASE` | `http://127.0.0.1:8765` | Where the runner sends CC requests |
| `ANTHROPIC_API_KEY` | `pax-cc-stub` | Placeholder (bridge accepts any non-empty value) |
| `PAX_CC_UPSTREAM` | `https://api.anthropic.com` | Upstream that the bridge forwards to |
| `PAX_CC_MAX_INLINE_RETRIES` | (unset) | Bridge-side transient-error retries |
| `PAX_CC_MAX_INLINE_WAIT` | (unset) | Max seconds bridge will pause inline |
| `PAX_BRIDGE_REQUEST_TIMEOUT` | `600` | Non-stream request timeout (seconds) |
| `PAX_BRIDGE_READ_TIMEOUT` | `180` | Non-stream per-chunk read timeout |
| `PAX_BRIDGE_STREAM_READ_TIMEOUT` | `600` | Streaming per-chunk read timeout |
| `PAX_BRIDGE_CONNECT_TIMEOUT` | `30` | TCP connect timeout |
| `PAX_CC_ACCOUNT_POOL` | (unset) | Path to JSON pool for multi-account failover |
| `PAX_CC_BUFFER_AND_RETRY` | `0` | Enable buffered-stream retry (A/B tests only) |

## Rate limits and quota

The bridge uses your **Claude Code subscription session quota**, not per-token API pricing. Pro/Max tiers each have three overlapping limits:

- Per-minute request rate (typically ~50 rpm)
- Rolling 5-hour message quota
- Per-day cap on some tiers

A single PAX benchmark run at `--concurrency 5` with multi-turn IPI cases can burst 300+ LLM calls in ~2 minutes and exhaust your 5-hour window. The runner does not cap concurrency for you.

**Rule of thumb:** for the full 30-case delivery, `--concurrency 5` completes in a few minutes and stays comfortably under Max quotas. Pro subscribers should start with `--concurrency 1` and scale up. Do not use the bridge for RL data generation or 10K+ episode runs — that is against Anthropic ToS and will lock your subscription.

Cost tracking notes: LiteLLM has native `anthropic/claude-*` pricing built in, so `cost_usd` in the trajectory JSON reports the equivalent **API list price** (a useful "what if this were metered" signal), not what your subscription actually costs. Real subscription cost is flat-rate — treat the reported number as an upper bound. Token counts and latency are accurate.

## Troubleshooting

**`credentials error: no Claude Code credentials found in Keychain`**
Run `claude login` and complete OAuth in your browser. Confirm the entry appears:
```bash
security find-generic-password -s "Claude Code" -w
```

**`connection refused` from benchmark**
The bridge is not running. Start it in terminal 1: `python -m nanobot.bridges.claude_code --port 8765`.

**`429 rate_limit_exceeded` or `PAX_CC_ACCOUNT_POOL` errors**
Subscription quota exhausted. Wait for the reset window (up to 5 hours) or switch to Bedrock: `--model glm`.

**Different port**
Both sides must agree. Start bridge with `--port 9000` and export `ANTHROPIC_API_BASE=http://127.0.0.1:9000`.

## Terms of service

Routing subscription-authenticated traffic through automated tooling is against Anthropic's ToS at scale. This bridge is intended for individual research and evaluation — running 30 benchmark cases against your own subscription. Do not use it to serve production traffic, generate training data at scale, or share subscription access.
