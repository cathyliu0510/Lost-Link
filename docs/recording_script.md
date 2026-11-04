# Lost Link – HW6 recording script (silent video, captions via `echo`)

## 0. Before you hit Record (checklist)
- [ ] **Tab 1 (server):** shows `Uvicorn running on http://127.0.0.1:8000`. Press **Cmd+K** to clear the screen. Never press Ctrl+C here.
- [ ] **Tab 2 (agents):** `echo $LOSTLINK_MODEL` prints `nvidia/nemotron-3.5-super-vl:free`. Then run `clear`.
- [ ] **Tab 3 (human):** `cd ~/Documents/lost-link && conda deactivate && source .venv/bin/activate && clear`
- [ ] Text enlarged (**Cmd+plus**, about 2 steps) in all tabs.
- [ ] Tab 1 and Tab 2 are separate windows, side by side. Tab 3 is a window you can switch to.
- [ ] Database is fresh. If not, run the reset block at the bottom first.
- [ ] Your key is not visible anywhere on screen.

**Start:** QuickTime Player → File → New Screen Recording → select the whole screen → Record.

---

## 1. Intro – Tab 2
```bash
echo "# Lost Link: a lost-and-found service that personal AI agents call directly (OpenAI Agents SDK + OpenRouter)"
```

## 2. Finder's agent – Tab 2
```bash
echo "# 1) Finder's agent (its own token) posts a found bottle; the sticker is stored as a PRIVATE detail"
python -m agents_demo.demo finder
```
Expect: `register_report(...) -> HTTP 200`, a report ID `F-XXXXXX`, 2× `CHECK PASS`.
Tab 1 shows: `finder-agent POST /v1/reports -> 200`

## 3. Owner's agent – Tab 2
```bash
echo "# 2) A DIFFERENT agent (owner) registers 'navy flask', searches, and claims - no human relaying"
python -m agents_demo.demo owner
```
Expect: 3 tool calls with HTTP 200, `candidates:` with the finder's report first, 5× `CHECK PASS`.
**Copy the case ID** `C-XXXXXX` from the output.
Tab 1 shows: `owner-agent POST /v1/reports`, `GET .../matches`, `POST /v1/claims`

## 4. Holder's human – Tab 3
```bash
echo "# 3) Only the holder's HUMAN can approve: compare the private detail with the claim"
python scripts/human.py inbox
python scripts/human.py approve C-XXXXXX --pickup "Hayden front desk, ask for Sam, 9-5"
```
Expect: the inbox shows `your_private_detail` next to `claim_message`, then `200` and `"decision": "approve"`.
Tab 1 shows: `human:finder-human POST .../decision -> 200`

## 5. Owner's agent reads the result, and misuse is refused – Tab 2
```bash
echo "# 4) Owner's agent reads the approval; agents trying to self-approve or edit others' reports are refused"
python -m agents_demo.demo status
python -m agents_demo.demo misuse
```
Expect: `server says: approved_for_pickup`, 2× `CHECK PASS`, then 3× `CHECK PASS` (403 / 422 / 403).

## 6. Verification + limitation – Tab 2
```bash
echo "# 5) Held-out check: correct report in the top 3, our matcher vs a category+keyword baseline"
python -m eval.eval_retrieval
echo "# Limitation: synthetic one-campus data and hand-written vocabulary; runs locally, not hosted"
```
Expect: `alias_matcher hit@3 10/10`, `baseline hit@3 3/10`.

**Stop:** click the stop button in the menu bar → File → Save.

---

## After recording
1. **Trim** the waits for the model. To cut from the middle, use iMovie: Cmd+B splits a clip, Delete removes a piece. About 60–90 s is fine.
2. **YouTube** → Create → Upload → Title: `Lost Link – MVP demo (MAS.665 HW6)` → Visibility **Unlisted** → copy the link.
3. **Spreadsheet** (HW6 sheet): fill in the members, the project title and the YouTube link.
4. **Canvas** → Text Entry: paste the paragraph from `docs/hw6_submission.md`, then the YouTube link.

## If something goes wrong
| Problem | Fix |
|---|---|
| `[rate limited ... retry]` | Wait. The demo retries on its own; cut the pause when editing. |
| `Still rate-limited` | `export LOSTLINK_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free` and rerun that step. |
| A `CHECK FAIL` | Rerun that same step once; the model's wording varies. |
| `Connection refused` | The server in Tab 1 stopped. Run the reset block. |
| You want a clean retake | Run the reset block, then start again from section 0. |

## Reset block (for a clean retake)
**Tab 1:**
```bash
# press Ctrl+C first
python scripts/setup_demo.py
uvicorn lostlink.server:app --port 8000 --no-access-log
```
**Tab 2:**
```bash
python scripts/setup_demo.py --seed
clear
```
**Tab 3:** `clear`, then press Cmd+K in Tab 1.
