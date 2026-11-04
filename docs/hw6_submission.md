# HW6 – MVP submission kit (Lost Link)

## 1. MVP paragraph (plain text, paste into Canvas)

Lost Link, as proposed in HW5, is a shared lost-and-found service built for AI agents, not people: it gives the personal agents of different people one place to post items, find matches, and make claims. In our demo, two separate AI agents (real LLMs via OpenRouter), each with its own access key, call our service through tool calls. The finder's agent posts a found blue water bottle and keeps a secret detail (a cactus sticker) private. The owner's agent posts a lost "navy flask", searches, and uses the returned top match to submit a claim on its own, with no person passing messages between them. Only the finder's human can approve the claim; the owner's agent then reads the approval and gives its user the pickup instructions. The server log in the video shows every call. Automatic checks on the real results confirm the right item ranked first, the secret detail never appeared in search, and requests using an agent's key to approve a claim or edit another agent's report were blocked. On 10 test queries, our matching found the right item 10/10 times, compared with 3/10 for simple keyword matching. Limitation: the test data is made up for one campus, and the service runs only on our laptop.

Video: <unlisted YouTube link> (please watch at 720p or higher so the text is readable: gear icon, then Quality, then 720p)

## 2. One-minute video (unlisted YouTube)

Layout: server log on the left (Tab 1), agents on the right (Tab 2), human console in Tab 3.
Record with QuickTime → File → New Screen Recording. Trim to about 60 s.

| Time | Screen | Say (roughly) |
|---|---|---|
| 0–7 s | README diagram | "Lost Link is a lost-and-found service that personal AI agents call directly. A human holder approves the pickup." |
| 7–17 s | `demo finder` + audit line `finder-agent POST /v1/reports` | "The finder's agent posts a blue bottle. The cactus sticker is stored privately." |
| 17–33 s | `demo owner`: three tool calls, the candidates, CHECK lines | "A different agent, with its own token, posts 'navy flask', searches, gets reasons like flask→bottle, and claims. The checks confirm the right report ranked first and the sticker never leaked." |
| 33–42 s | `human.py inbox` then `approve` | "Only the holder's human session can approve. Here the claim matches the private detail." |
| 42–52 s | `demo status` → approved_for_pickup; `demo misuse` → 403/422 | "The owner's agent now gets the pickup instructions. If an agent tries to approve itself, it's refused." |
| 52–60 s | `python -m eval.eval_retrieval` table | "Held-out queries: 10/10 in the top 3 versus 3/10 for the baseline. Limitation: synthetic data for one campus, running locally." |

Tip: do one rehearsal run first. Then reset (`python scripts/setup_demo.py`, restart the server, `--seed`) so the IDs on screen are clean. Run `clear` in Tab 2 after the `export` lines so your OpenRouter key never appears in the video.

## 3. Class team spreadsheet
In the HW6 sheet (a different sheet from the HW5 one), update:
- [ ] Team members: Kemeng Zhang, Yicheng Liu
- [ ] Project title/idea: Lost Link – shared lost-and-found service for personal AI agents (register, match, private claim, human-approved pickup)
- [ ] Unlisted YouTube link

## 4. Canvas
- [ ] Paste the paragraph from section 1 , then the YouTube link on its own line
- [ ] Kemeng also submits, unless Canvas treats HW6 as a group submission

## 5. Rubric self-check
- **Agentic Web fit (3):** The service is agent-facing. Two independent agents use it with separate identities. The service adds shared state, matching and claim rules that neither agent has on its own.
- **End-to-end core (4):** A real agent request goes through function tools to HTTP, the server executes it (visible in the audit log), and the agent uses the returned candidate ID to make the claim. No human relays steps between the agents; the only human step is the approval, which is intended.
- **Verification + limitation (2):** CHECK lines are computed from the real tool outputs. The held-out eval compares against the baseline. The limitation is stated in the paragraph and at the end of the video.
- **Submission + listing (1):** Video, paragraph and spreadsheet row.
