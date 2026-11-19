# HW9: agent usability — code, documentation and execution evidence

Lost Link lets a personal agent register lost/found reports, retrieve candidates,
submit a private claim and read its case status. A human holder authorizes pickup.
This directory's evidence concerns an actual local FastAPI/SQLite service, not the
separate browser-only public demo.

## What changed

- [Agent interface guide](docs/AGENT_GUIDE.md): capability, setup, access, schemas,
  outputs, permissions, errors, limits and one small unrelated example.
- A fresh-session agent used those instructions and its own authorized token to
  attempt a natural-language recovery task. Its requests, returned data, decision,
  user-facing outcome and independent database snapshot are preserved below.
- Impossible or noncanonical dates now return **422** on both report creation
  and modification. Null remains valid for an unknown date on creation; null in a
  PATCH retains the existing value. Invalid creation does not consume an
  idempotency key; invalid modification does not consume a version.
- Portable operator commands prepare a new isolated experiment and preserve the
  original evidence. A credential-free checker cross-checks the recorded run.

## Recorded cold-start run

The pre-run [plan](eval/hw9/recorded/plan.json) defined six useful-result checks
before the client started; its [manifest](eval/hw9/recorded/pre_run_manifest.json)
records the input and harness hashes. The client received only the interface
guide, its own access file and a user task. It did not receive the project source,
fixtures, target IDs, expected answer or a sequence of API calls. The unrelated
documentation example registers lost keys; the task was a lost flask.

**Context:** self-run fresh Codex session (`fork_turns=none`), not another builder's
independent agent. The operator provisioned synthetic records, authorized access,
started the service and recorded HTTP. No messages coached the client's choices
or API-call order during the run. The documentation-only input restriction was
an instruction boundary, not an operating-system isolation guarantee.

Task: on November 18, help a user who lost a navy flask in the library yesterday,
does not know the brand and remembers a green cactus sticker near the cap.

| Actual interaction | Observed result / use |
| --- | --- |
| POST report | `L-9F69A3`; brand kept null; date resolved to `2026-11-17` |
| GET matches | Blue bottle `F-C60E22`: 0.94; conflicting thermos: 0.47 |
| POST claim | Client used the returned candidate ID; case `C-5A56DA` |
| GET case | Actual status `submitted`; no human decisions or pickup instructions |

All four HTTP requests succeeded with 200. The six predeclared checks passed:
facts preserved, returned ID used, correct report/case linkage, actual status
consumed, no false approval/return and holder's hidden verification sentinel
withheld. The [user message](eval/hw9/recorded/coldstart/user_message.txt) accurately
reports a submitted claim awaiting review and explains the next step. This is a
useful recovery request; ownership, pickup and physical return were **not** completed.
Scores are retrieval heuristics, not ownership probabilities.

Checkable evidence:

- [Client request/response log](eval/hw9/recorded/coldstart/request_response.jsonl)
  and [server HTTP log](eval/hw9/recorded/evidence/http.jsonl).
- [Client decision and outcome](eval/hw9/recorded/coldstart/client_result.json),
  [state](eval/hw9/recorded/coldstart/client_state.json) and agent-authored
  [client code](eval/hw9/recorded/coldstart/client.py).
- [Independent SQLite/audit snapshot](eval/hw9/recorded/evidence/coldstart_verification.json).
  The snapshot was taken at the end of the client run, before the boundary probe.
- [Exact original guide](eval/hw9/recorded/coldstart/AGENT_GUIDE.md),
  [task](eval/hw9/recorded/coldstart/task.txt) and
  [instrumented service](eval/hw9/recorded/experiment.py).

One initial connection failed because the sandbox blocked loopback access.
Execution approval allowed the same saved intent to complete; this was test setup,
not an API failure. The client also mistakenly displayed its ephemeral token in
its private tool output. It disclosed the incident; the token was
[revoked](eval/hw9/recorded/evidence/credential_rotation.json). Access files, human
tokens, raw private fixtures and the database are excluded from published evidence.
The saved client code/logs contain no credential values. Credential handling was
therefore imperfect even though the task checks passed.

## Boundary, improvement and regression

The predeclared probe used `date: "2026-02-30"`. A date contract should reject an
impossible day, but the [original run](eval/hw9/recorded/evidence/boundary_before.json)
returned **200** and stored it. Retrieval's parser would treat it as unknown, so an
agent could receive a successful creation despite losing the date evidence.

The shared date validator now requires a real calendar day in exact `YYYY-MM-DD`
form on POST and PATCH. The [same HTTP probe after the first fix](eval/hw9/recorded/evidence/boundary_after.json)
returned **422** with a `body.date` error. A follow-up code audit found that PATCH
also accepted dates; the final change covers that route and corrects the guide's
earlier statement that date was not patchable. The original guide stays unchanged
in the record. The [final HTTP regression](eval/hw9/recorded/evidence/postfix_http_regression.json)
checks the completed implementation and is an operator-run regression, not a
second cold-start agent experiment.

[Focused tests](tests/test_hw9_dates.py) exercise impossible days, an invalid
month, a non-leap February 29, relative text, basic ISO dates and ISO week dates
on POST and PATCH; they also check a valid leap day, a normal date and null.
They verify that rejection neither persists a bad edit nor consumes a request
ID/version. The complete suite passes **26 tests**, including existing privacy,
permissions, retries, state-machine, matcher and live dashboard checks.

This fixes validation for new writes. It does not migrate historical invalid
rows, expand the English matcher vocabulary, prove performance beyond one small
synthetic cold-start task or establish production security. The deliberate bad
row from the original probe was not retroactively cleaned to improve the result.

## Reproduce and inspect

From this HW9 branch, with Python 3.11/3.12:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install fastapi uvicorn httpx pytest
.venv/bin/python -m pytest -q
.venv/bin/python -m eval.hw9.verify
```

The verifier needs only the standard library and checks the **existing record**;
it does not claim a new cold-start test. Hashes are local provenance evidence,
not an externally notarized timestamp. The original access-file hash is retained
for provenance, but that file is intentionally unavailable.

To conduct a **new** test, choose a nonexistent disposable directory and ensure
loopback port 8869 is free. Keep it outside the source tree (or in `.hw9-runs/`).

```bash
.venv/bin/python -m eval.hw9.run prepare --run-dir /tmp/lost-link-hw9-new
.venv/bin/python -m eval.hw9.run serve --run-dir /tmp/lost-link-hw9-new
```

`prepare` generates new credentials and IDs, copies the current guide, freezes
the natural task and checks, and records source/input hashes. `serve` seeds three
synthetic found records into a new SQLite database and records real HTTP traffic.
The frozen instrumentation uses the explicit `LOSTLINK_PROJECT_ROOT` override;
the launcher supplies this checkout's path automatically. No model provider/API
key is needed to run the service or the tests.

Start a genuinely fresh client session with only these three files:

1. `/tmp/lost-link-hw9-new/coldstart/AGENT_GUIDE.md`
2. `/tmp/lost-link-hw9-new/coldstart/access.json` (read privately; never print it)
3. `/tmp/lost-link-hw9-new/coldstart/task.txt`

Do not give the new agent this readme, the recorded client code/logs, expected IDs,
source or `private/`. Do not coach its call order. Let it choose its tools/actions
and save its actual requests, decisions and final user message. Compare its HTTP
record with `private/service.db`, its reports/cases/audit log, and the six checks
in `plan.json`; inspect its user-facing claims separately. Record independence,
setup approvals and any manual help truthfully. New IDs and decisions may differ.
Stop the service with Ctrl-C and revoke/delete disposable access afterward.

The original recorded client code is **evidence of that client's choices**.
Replaying it is a scripted regression, not a fresh documentation-only test.

This package covers the software portion of HW9. Slides, video, team PDF and
Canvas submission are outside this code-only scope.
