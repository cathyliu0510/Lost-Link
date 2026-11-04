# Lost Link

A shared lost-and-found service that **people's personal AI agents** call directly.
Agents register lost/found reports, search for candidates, submit private claims and
check case status. The item holder's **human** approves the pickup. An agent can't.

MIT MAS.665 (AI Studio, Fall 2026) team project: Kemeng Zhang, Yicheng Liu.
Current status and next steps are in [`PROGRESS.md`](PROGRESS.md).

```
finder-agent ──register_report──┐
                                ▼
owner-agent ──register_report──► Lost Link API (FastAPI + SQLite)
            ──find_matches─────►   • alias matching + reasons + unknown fields
            ──submit_claim─────►   • per-agent tokens, owner-only access
            ──get_case_status──►   • private_detail never returned to agents
                                   • one approval per found item, idempotent retries
finder-human ──scripts/human.py─► /v1/human/*  (approve / need_info / reject / returned)
```

## Repository layout

| Path | What it is |
|---|---|
| `lostlink/server.py` | The service: endpoints, auth, case state machine, audit log |
| `lostlink/matching.py` | Alias matcher + HW5 baseline (category + keyword) |
| `agents_demo/tools.py` | OpenAI Agents SDK function tools, bound to one agent's token |
| `agents_demo/demo.py` | Runs the finder / owner agents and checks their real tool outputs |
| `scripts/human.py` | Holder's human console (terminal stand-in for a dashboard) |
| `scripts/setup_demo.py` | Creates tokens, resets the DB, seeds 20 synthetic found reports |
| `eval/eval_retrieval.py` | Top-3 retrieval on 10 held-out queries vs the baseline |
| `tests/test_service.py` | 8 tests: leaks, permissions, retries, version conflicts, single approval |
| `data/` | Synthetic reports (AI-generated) and held-out queries |
| `docs/` | HW6 submission text and the demo recording script |

## Setup (macOS, Python 3.11+)

```bash
cd lost-link
conda deactivate                      # only if Anaconda's (base) is active
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q                   # expect: 8 passed
python -m eval.eval_retrieval         # expect: 10/10 vs 3/10
```

Use `python -m pytest` / `python -m pip` so the venv's copies are used, not Anaconda's.

## Run the demo (3 terminal tabs)

Every new tab: `cd ~/Documents/lost-link && conda deactivate && source .venv/bin/activate`.

**Tab 1 – server** (shows the audit log; never type here while it runs)
```bash
python scripts/setup_demo.py                       # new tokens + empty DB
uvicorn lostlink.server:app --port 8000 --no-access-log
```

**Tab 2 – agents**
```bash
python scripts/setup_demo.py --seed                # 20 found reports (10 real + 10 decoys)
export LOSTLINK_PROVIDER=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...             # never commit or screen-share this
export LOSTLINK_MODEL=nvidia/nemotron-3.5-super-vl:free
clear
python -m agents_demo.demo finder                  # finder's agent posts the blue bottle
python -m agents_demo.demo owner                   # owner's agent: register -> search -> claim
```

**Tab 3 – holder's human**
```bash
python scripts/human.py inbox                      # private detail next to the claim message
python scripts/human.py approve $(python -c "import json;print(json.load(open('demo_state.json'))['case_id'])") \
  --pickup "Hayden front desk, ask for Sam, 9-5"
```

**Back in Tab 2**
```bash
python -m agents_demo.demo status                  # owner's agent reads approved_for_pickup
python -m agents_demo.demo misuse                  # agent-key requests to approve/edit -> 403/422
```

Optional: `python scripts/human.py returned <case_id>` closes the case after the hand-over.

### Model providers
Any OpenAI-compatible endpoint with tool calling works (`LOSTLINK_PROVIDER`):

| Provider | Env vars | Notes |
|---|---|---|
| `openrouter` | `OPENROUTER_API_KEY`, `LOSTLINK_MODEL` | Used for the HW6 video. Free models: 50 requests/day; a full run uses ~10 |
| `gemini` | `GEMINI_API_KEY` (optional `LOSTLINK_MODEL`) | Default `gemini-2.5-flash` |
| `ollama` | `LOSTLINK_MODEL` | Local, no key; small models often skip tool calls |
| `openai` | `OPENAI_API_KEY` | Default `gpt-4.1-mini` |

List OpenRouter free models that support tools:
```bash
curl -s https://openrouter.ai/api/v1/models | python -c "import json,sys;[print(m['id']) for m in json.load(sys.stdin)['data'] if m['id'].endswith(':free') and 'tools' in (m.get('supported_parameters') or [])]"
```

### Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `address already in use` | An old server is running: `kill $(lsof -ti :8000)`, then restart uvicorn |
| Agent says "system error", `CHECK FAIL: registered` | Server in Tab 1 is down; restart it and `--seed` |
| `401 User not found` | Wrong/deleted OpenRouter key in this tab |
| `429` / `rate limited ... retry` | Free model busy; the demo retries. Otherwise switch `LOSTLINK_MODEL` |
| Owner agent claims nothing (two near-identical candidates) | Leftover reports from an earlier run. Reset: Tab 1 `setup_demo.py` + restart, Tab 2 `--seed` |
| `404 case not found` on approve | Wrong case ID; use the `$(...)` form above |

## What the demo checks automatically
`CHECK PASS/FAIL` lines are computed from the **JSON the tools actually returned**, not the model's text:
- the owner agent's top candidate is the report the finder agent created
- the finder's private detail never appears in search results
- the claim targets that report
- pickup instructions appear only after a human `approve`; status is not `returned` before hand-over
- `misuse`: agent key on the human endpoint → 403; forged `human_approved` field → 422; editing another agent's report → 403

## Results

**Live run** (OpenRouter `nvidia/nemotron-3.5-super-vl:free`, 2026-10-28): all checks passed. Top candidate scored 0.95 vs 0.71 for the next one.

**Retrieval eval** (`python -m eval.eval_retrieval`, 10 held-out paraphrased lost reports, 20 visible found reports):

| Ranker | hit@3 | mean wrong in top 3 | no candidate |
|---|---|---|---|
| Alias matcher | 10/10 | 1.0 | 0 |
| Category + keyword baseline | 3/10 | 0.3 | 7 |

The baseline misses mostly because it needs the exact category word (`flask` ≠ `water bottle`).
Our matcher returns about one wrong candidate per query, so the agent still reads the reasons and the holder still verifies.

## Limitations
- Synthetic data, held-out queries and vocabulary were written by our team (with AI help) for one campus; 10/10 likely overstates performance on real wording.
- Runs locally on SQLite with tokens in a local file; not yet a hosted HTTPS service with real accounts.
- Human console is a terminal script; no notifications (agents poll `get_case_status`).
- Text only, no photos.
