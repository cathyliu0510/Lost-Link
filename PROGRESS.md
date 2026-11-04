# Lost Link: Progress and Handoff

*Last updated: 2026-11-04*

**Team:** Kemeng Zhang, Yicheng Liu (Harvard Data Science), MIT MAS.665 AI Studio, Fall 2026.

## 1. What Lost Link is
Lost Link is a shared lost-and-found service for **personal AI agents** ("build X for agents"). It gives the agents of different people one place to:
- register lost and found reports,
- get ranked match candidates with reasons,
- submit private claims,
- check case status.

A human holder approves each pickup. Agents can't approve anything themselves.

## 2. Milestone status

| Milestone | Status | Notes |
|---|---|---|
| **HW5: Proposal** | Done (confirm Canvas) | English one-page proposal; AI-reviewer feedback included. Listed on the class Project Ideas tab (ID 59) and the Students tab (team "Lost Link"). Both members should confirm their Canvas submission. |
| **HW6: MVP** | Built and recorded; **submission pending** | Working core verified live with a real LLM. See section 4 for the remaining steps. |
| Final project | Not started | Ideas in section 7. |

## 3. What's built and verified

| Piece | State |
|---|---|
| FastAPI service (`lostlink/server.py`) | Done. Per-agent tokens, owner-only access, private detail never returned, idempotent retries, version conflicts (409), one approval per found item, human-only approval, audit log |
| Matcher (`lostlink/matching.py`) | Done. Category, colour and location aliases, date window, `unknown` handled as neutral, readable reasons |
| Agent clients (`agents_demo/`) | Done. Two OpenAI Agents SDK agents (finder, owner), each with its own token; provider switch (OpenRouter / Gemini / Ollama / OpenAI); automatic retry on 429 |
| Human console (`scripts/human.py`) | Done. inbox, approve, need-info, reject, returned |
| Tests | 8/8 pass (`python -m pytest -q`) |
| Retrieval eval | Alias matcher 10/10 hit@3 vs baseline 3/10 on held-out queries |
| Live end-to-end run | **Passed** on 2026-10-28 with OpenRouter `nvidia/nemotron-3.5-super-vl:free`. Finder registered → owner registered, searched and claimed (top match 0.95 vs 0.71) → human approved → owner read `approved_for_pickup` → misuse requests got 403/422/403 |
| Extra behaviour observed | With two near-identical bottles in the DB (0.967 vs 0.957), the owner agent **declined to claim** and asked for more detail instead of guessing |

## 4. HW6: what's left to submit
Deliverables: a ~1-minute unlisted YouTube video, one short paragraph, and the class spreadsheet row.

- [ ] **Trim the video** to about 60 s, 75 s at most. Cut the model "thinking" pauses. Keep:
  - the captions
  - the 3 owner tool calls with HTTP 200
  - all `CHECK PASS` lines
  - the inbox and the `200` approve
  - `approved_for_pickup`
  - the misuse 403/422
  - the eval table
  - the Tab 1 audit log
  
  Make sure no API key and nothing from earlier failed takes appears.
- [ ] **Upload to YouTube as Unlisted** (not Private). Title: `Lost Link – MVP demo (MAS.665 HW6)`. Wait until 720p is available.
- [ ] **HW6 team spreadsheet:** fill in the members (Kemeng Zhang, Yicheng Liu), the title ("Lost Link – shared lost-and-found service for personal AI agents"), and the YouTube link.
- [ ] **Canvas text entry:** paste the paragraph from [`docs/hw6_submission.md`](docs/hw6_submission.md) and replace `<unlisted YouTube link>` with your link.
- [ ] **Kemeng also submits**, unless Canvas treats HW6 as a group submission.
- [ ] **Security:** delete the OpenRouter key starting `sk-or-v1-e08…`, which was exposed in a chat. Make a new key with a small spending limit.

**Expected score against the rubric:** 9.5–10/10. The main risks are a video well over a minute, or missing execution evidence (the audit log, the tool calls) after trimming.

## 5. How to run
Full steps are in [`README.md`](README.md). In short:
1. **Tab 1:** `setup_demo.py` + `uvicorn`.
2. **Tab 2:** `--seed` + the `export` lines, then `finder` and `owner`.
3. **Tab 3:** `inbox` + `approve`.
4. **Tab 2:** `status` and `misuse`.

The silent-video recording script with `echo` captions is in [`docs/recording_script.md`](docs/recording_script.md).

**Lessons from the recording sessions:**
- **Reset fully before each take:** `setup_demo.py` in Tab 1, restart the server, then `--seed` in Tab 2. Leftover reports make the owner agent see a tie and refuse to claim.
- **Run the steps strictly in order:** owner → human approve → status. If `status` runs before the approval, it correctly shows `submitted`.
- **Free OpenRouter models allow 50 requests/day.** One take uses about 10–12. Check the remaining count:
  `curl -s https://openrouter.ai/api/v1/key -H "Authorization: Bearer $OPENROUTER_API_KEY"` (look at `free_model_daily_requests`).
- `google/gemma-4-31b-it:free` returned 429 repeatedly; `nvidia/nemotron-3.5-super-vl:free` worked.
- If Anaconda is installed, run `conda deactivate` in every tab. Use `python -m pytest` and `python -m pip`.

## 6. Design decisions (keep consistent)
- **Interface:** HTTPS JSON API plus function tools. MCP is deferred.
- **Case states:** `submitted → needs_clarification → submitted`; `submitted → approved_for_pickup → returned`; `submitted → rejected`.
- **Approval:** only the holder's human token can call `/v1/human/*`. Agent tokens get 403, and a forged `human_approved` field gets 422 (`extra="forbid"`).
- **Privacy:** `private_detail` is stored but never returned by agent endpoints. `missing` lists only the caller's own empty fields, so it can't hint at the holder's private answer.
- **Matching is not ownership:** candidates are suggestions. The human compares the claim with the private detail.
- **Scope kept small:** text only, synthetic data, one campus, no notifications, one agent framework.

## 7. Ideas for the final project (not decided)
- **Fix the stated limitations:**
  - Host the API on HTTPS (for example Render, or Maritime for students) with Postgres.
  - Real accounts and tokens in place of `secrets.json`.
- **Add an MCP server** so Claude, Gemini CLI and other harnesses can use the same tools.
- **Web dashboard for the holder** in place of `scripts/human.py`.
- **Small pilot with classmates** to test the open assumption from HW5: do real holders answer clarification requests within 24 hours? Also test matching on real wording.
- **Larger, harder evaluation set,** for example near-duplicate items and missing fields, written by someone other than the vocabulary author.

## 8. Where things live
- **GitHub repo:** this folder. `.gitignore` keeps `secrets.json`, `.env.agents`, `lostlink.db`, `demo_state.json` and `.venv/` out of git.
- **Claude Project "MAS665 Project":**
  - HW5 brief
  - Chinese handoff notes
  - HW6 submission kit
  - MVP README
- **Class sheets:**
  - Project Ideas / Students tabs (HW5)
  - HW6 team spreadsheet (the link is in the HW6 instructions)
