# Lost Link: interface guide for a new client agent

Lost Link is shared lost-and-found infrastructure for personal AI agents.
An authorized agent can register reports, search for candidates, privately
claim a found item and check the resulting case. A matching score is a lead,
not proof of ownership. The human holding the item decides whether to release it.

## Access and setup

The current API is a local Python/FastAPI/SQLite prototype. The public dashboard
is a separate synthetic-data interaction demo, not a hosted production API.
Your operator provides a JSON access file containing `base_url` and
`agent_token`. Send `Authorization: Bearer <agent_token>` on agent requests.
Do not print, upload or put the token in a URL. You receive only your own agent
identity. Keep credentials outside prompts sent to any additional service.

An operator starting a new server can use Python 3.11/3.12. Extract the supplied
`Lost_Link_HW9_code.zip` and enter `Lost-Link-HW9/`, or use an existing checkout
of the HW9 branch. Run these commands from that source root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install fastapi uvicorn httpx
```

The upstream project is `https://github.com/cathyliu0510/Lost-Link`. Its main
branch at `c26cddbfc9721c12acafa4603f70265c6f37bd11` is the experiment's service
baseline; use the supplied HW9 source for the date-validation improvement.

Configure `LOSTLINK_DB` to a disposable SQLite path and `LOSTLINK_SECRETS` to
a JSON file with `agents` mapping random tokens to agent IDs, and `humans`
mapping separate random tokens to `{ "name": "holder", "acts_for": "finder" }`.
Then run `.venv/bin/python -m uvicorn lostlink.server:app --host 127.0.0.1 --port 8000`.
Do not expose this local credential-file prototype to the public Internet.
`/openapi.json` describes the machine-readable schema of the running service.

## Requests and responses

All request bodies are JSON. Unrecognized body fields are rejected (422).
IDs are opaque: use IDs returned by the service, not invented or example IDs.

| Operation | Inputs | Returned result / rules |
| --- | --- | --- |
| `POST /v1/reports` | Required: `kind` (`lost` or `found`), public `description`, client-chosen `request_id`. Optional: `category`, `color`, `brand`, `location`, `date` (ISO `YYYY-MM-DD` or null), `private_detail`. | `report_id`, `version`, `duplicate_request`. Missing information should be null, not guessed. Put a finder's verification clue in `private_detail`, never in the public description. |
| `PATCH /v1/reports/{id}` | Your own report's `expected_version`, plus changed `category`, `color`, `brand`, `location`, `date`, or `description`. | New `version`; another agent's record is forbidden (403); stale version is a conflict (409). Date changes use the same validation as creation. Null fields leave existing values unchanged; private-detail changes are not supported. |
| `GET /v1/reports/{lost_id}/matches` | Your own lost report ID. Optional query parameter `limit` (default 3, maximum 5). | `candidates` with `report_id`, `score`, `reasons`, `unknown`, `conflicts`, and public `found_report`; `missing` lists fields absent from your report. Candidate IDs can be used in claims. The score is not a calibrated ownership probability. |
| `POST /v1/claims` | `lost_report_id` (your own), `found_report_id` (an open found record), private `claim_message`, client-chosen `request_id`. | `case_id`, `status`, `duplicate_request`. Reusing the same request ID and payload safely retries creation. Use PATCH, not creation retries, to change a report. |
| `GET /v1/cases/{case_id}` | A case ID returned by a claim. | `status`, associated found ID, any clarification question and human-decision history. Only case parties may read it. Pickup instructions appear only after human approval. |
| `POST /v1/cases/{case_id}/info` | `text`, answering a pending clarification. | Case ID and status. Only the claimant can reply, and only in `needs_clarification`; otherwise 403/409. |

Case states are `submitted`, `needs_clarification`, `rejected`,
`approved_for_pickup` and `returned`. A request for more information can lead
back to `submitted`. Never tell the user that pickup is approved or an item
was returned unless the service actually reports that state.

## Permissions and limitations

Human endpoints under `/v1/human/` require a separate `X-Human-Token` that is
not supplied to agent clients. Agent credentials cannot approve a pickup.
Do not add an approval flag to a claim. You may describe the human action
still required in your final message. The holder may use their own console
to request more information, approve, reject or confirm the hand-over.

The matcher uses a small hand-written English vocabulary and structured
public fields, not a general embedding or image search. Recognized types
include bottles/flasks, phones, earbuds, keys, wallets, ID cards, umbrellas,
laptops, chargers, jackets, backpacks, glasses, calculators and notebooks.
Color and campus-location aliases are normalized. Unsupported or missing
category evidence may produce an empty candidate list. Unknown information
must remain unknown. Private verification fields never appear in search.

401 means invalid agent access; 403 means a permission boundary; 404 means
an unknown ID; 409 means a state/version conflict; 422 means invalid inputs.
Inspect the returned JSON before changing a request. Stop and report a genuine
service or setup error rather than pretending the task succeeded.

The HW9 validation improvement rejects impossible calendar dates and alternate
formats with 422 on the `date` field for both creation and modification. For an unknown date at creation, send null; do not
send a relative word such as "yesterday". This validation affects new reports;
it does not repair older stored records. An explicit null in a PATCH leaves
the date unchanged. The HW9 branch includes the validation change and focused
regression tests. The preserved original client-input guide remains in the
evidence bundle, including its earlier incorrect statement that date could
not be patched; this corrected guide matches the implementation.

## One small independent example

This registers a lost-key report only. It is not a task walkthrough or an
expected answer. Replace the example values with facts supplied by your user.

```python
import json, httpx
access = json.load(open("access.json"))
response = httpx.post(access["base_url"] + "/v1/reports",
    headers={"Authorization": "Bearer " + access["agent_token"]},
    json={"kind": "lost", "description": "silver keys",
          "category": "keys", "color": "silver", "location": None,
          "date": None, "request_id": "keys-example-unique"}, timeout=10)
print(response.status_code, response.json())
```

For repeatable HW9 experiments, use the accompanying experiment package. It
creates its own credentials and fixtures, records HTTP traffic, and checks
the actual database separately. Fresh-client decisions and outputs must come
from the client; the operator must not supply its call order or the answer.
