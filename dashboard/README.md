# Lost Link interactive dashboard

A dark, responsive workspace that makes the existing lost-and-found workflow
visible: agent activity on the left; candidates, case status and human review
on the right. No production service code is changed.

## Two explicit modes

- **Local API connected**: the UI bridge starts a real, unmodified Lost Link
  HTTP service in a subprocess, with a fresh disposable SQLite database and
  separate random finder, owner and human credentials. Actual response codes
  and sanitized service results appear in the execution log.
- **Interactive / synthetic data**: the standalone hosted preview uses a
  browser-only state machine. It demonstrates interactions, not live backend
  execution, LLM behavior or service security. Its local scoring approximates
  the demo examples; it is not the production matcher or a benchmark.

Neither mode calls a model. Participants execute the user's explicit demo
actions. The human tab is deliberate manual role switching for a single-user
demonstration, not production account authentication. It uses synthetic clues
and creates no physical hand-over evidence.

## Local run

From the project root, use a Python 3.11+ environment containing FastAPI,
uvicorn, httpx and pytest (already included in the project's requirements):

```bash
python -m dashboard --port 8765
```

Open `http://127.0.0.1:8765`. The initial search runs on the default sample.
Choose a candidate, submit a private claim, switch to human review, request a
clarification, switch back to answer, approve with pickup instructions, then
confirm hand-over. The sidebar also demonstrates absence, retries and a real
403 rejection of an agent approval request in local mode.

The server binds only 127.0.0.1. Reset/exit affect only the temporary demo
service and database; existing `secrets.json` and `lostlink.db` are not used.
Credentials stay in the bridge process, not in JavaScript or exported logs.
The HTTP endpoints are demo controls for one local operator, not a deployed
multi-user service. Stop with Ctrl+C. No package installation is needed for
the buildless frontend in `web/`.

## Verify

```bash
python -m pytest -q tests/test_dashboard.py
```

The test starts a temporary loopback service and exercises privacy withholding,
claim/clarification/approval/return, misuse rejection, retries and the absent
category. Socket binding must be allowed.

The online preview contains only `web/` assets and is clearly labelled as
interactive synthetic data. It does not publish the local bridge or its API.
