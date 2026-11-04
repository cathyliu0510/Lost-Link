"""
End-to-end demo: two independent OpenAI Agents SDK agents use Lost Link.

    python -m agents_demo.demo finder     # finder's agent registers the found item
    python -m agents_demo.demo owner      # owner's agent registers, searches, claims
    python scripts/human.py inbox / approve ...   # holder's human decides (separate terminal)
    python -m agents_demo.demo status     # owner's agent reads the decision
    python -m agents_demo.demo misuse     # owner's token tries to self-approve etc.

Each agent process loads ONLY its own token. After each step the script runs
automatic checks on the actual tool results (printed as CHECK lines).
"""
import argparse
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI, RateLimitError

from .tools import BASE, CALL_LOG, make_tools

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "demo_state.json"
ENV = dict(l.split("=", 1) for l in (ROOT / ".env.agents").read_text().split())
# ---------------------------------------------------------------------------
# Model provider. Any OpenAI-compatible endpoint with tool calling works, so
# the free options from the class "Free AI Credits" doc can replace OpenAI:
#   LOSTLINK_PROVIDER=openai      OPENAI_API_KEY      (default model gpt-4.1-mini)
#   LOSTLINK_PROVIDER=gemini      GEMINI_API_KEY      (default model gemini-2.5-flash)
#   LOSTLINK_PROVIDER=openrouter  OPENROUTER_API_KEY  (set LOSTLINK_MODEL, e.g. a ":free" model with tools)
#   LOSTLINK_PROVIDER=ollama      no key, local       (set LOSTLINK_MODEL, e.g. qwen3:8b)
# ---------------------------------------------------------------------------
PROVIDERS = {  # name -> (base_url, api-key env var, default model)
    "openai": (None, "OPENAI_API_KEY", "gpt-4.1-mini"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/",
               "GEMINI_API_KEY", "gemini-2.5-flash"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", None),
    "ollama": ("http://localhost:11434/v1", None, None),
}
PROVIDER = os.environ.get("LOSTLINK_PROVIDER", "openai")


def build_model():
    """Return a model name (OpenAI) or a Chat Completions model on another
    OpenAI-compatible endpoint. Exits with a clear message if config is missing."""
    base_url, key_var, default = PROVIDERS[PROVIDER]
    name = os.environ.get("LOSTLINK_MODEL", default)
    if not name:
        sys.exit(f"Set LOSTLINK_MODEL for provider '{PROVIDER}'")
    key = os.environ.get(key_var) if key_var else "ollama"
    if not key:
        sys.exit(f"Set {key_var} first (export {key_var}=...)")
    if PROVIDER == "openai":
        return name
    set_tracing_disabled(True)  # traces upload to OpenAI; off for other providers
    return OpenAIChatCompletionsModel(model=name,
                                      openai_client=AsyncOpenAI(base_url=base_url, api_key=key))


MODEL = None  # set in __main__ (tests may inject their own model)
TODAY = date.today()

# What each human tells their own agent (overridable with --say).
FINDER_SAYS = ("I picked up a blue water bottle on the 2nd floor of Hayden Library "
               "yesterday afternoon. It has a green cactus sticker near the cap, "
               "keep that private so we can check the real owner. Please post it.")
OWNER_SAYS = ("I lost my navy flask, I think in the library yesterday. Brand unknown. "
              "If you find it, tell them it has a cactus sticker by the lid.")


def save_state(**kv):
    s = json.loads(STATE.read_text()) if STATE.exists() else {}
    s.update(kv)
    STATE.write_text(json.dumps(s, indent=2))
    return s


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def check(label: str, ok: bool):
    print(f"CHECK {'PASS' if ok else 'FAIL'}: {label}")
    return ok


def run(agent: Agent, text: str, attempts: int = 4, wait_s: int = 20):
    """Run one agent turn. Free models often return 429 (rate limited), so
    retry with a growing pause. Re-running is safe: register/claim tools send
    a deterministic request_id, so the server de-duplicates repeated calls."""
    print(f"\n>>> user -> {agent.name}: {text}\n")
    for i in range(1, attempts + 1):
        try:
            result = Runner.run_sync(agent, text, max_turns=12)
            break
        except RateLimitError:
            if i == attempts:
                sys.exit("Still rate-limited. Wait a few minutes or set LOSTLINK_MODEL "
                         "to another ':free' model, then rerun this step.")
            print(f"  [rate limited by the model provider; retry {i}/{attempts - 1} in {wait_s * i}s]")
            time.sleep(wait_s * i)
    print(f"\n<<< {agent.name}: {result.final_output}\n")


def common_rules() -> str:
    return (f"Today is {TODAY.isoformat()} (yesterday = {(TODAY - timedelta(days=1)).isoformat()}). "
            "Use ISO dates; use null for anything your user did not say. Never put private "
            "verification details in the public description.")


def finder_step(say: str):
    t = make_tools(ENV["FINDER_AGENT_TOKEN"], "finder-agent")
    agent = Agent(
        name="finder-agent", model=MODEL, tools=[t["register_report"]],
        instructions=("You are the personal agent of someone who found an item. Register it "
                      "with Lost Link as kind='found'. Put the detail only the owner would know "
                      "in private_detail. Then tell your user the report_id. " + common_rules()))
    run(agent, say)
    regs = [c for c in CALL_LOG if c["tool"] == "register_report" and c["status"] == 200]
    if check("finder agent registered a found report", bool(regs)):
        a = regs[-1]["args"]
        save_state(finder_report_id=regs[-1]["result"]["report_id"],
                   finder_private_detail=a["private_detail"] or "")
        check("private detail kept out of public description",
              not a["private_detail"] or a["private_detail"].lower() not in a["description"].lower())


def owner_step(say: str):
    t = make_tools(ENV["OWNER_AGENT_TOKEN"], "owner-agent")
    agent = Agent(
        name="owner-agent", model=MODEL,
        tools=[t["register_report"], t["find_matches"], t["submit_claim"], t["get_case_status"]],
        instructions=(
            "You are the personal agent of someone who lost an item. Steps: (1) register a "
            "kind='lost' report; (2) call find_matches; (3) read reasons, unknown and conflicts. "
            "If one candidate is clearly the most plausible, submit_claim with the private details "
            "your user remembers; if two are equally plausible, claim neither and explain. "
            "(4) Report the case_id and status. A match is NOT proof of ownership; a human holder "
            "decides. " + common_rules()))
    run(agent, say)

    # ---- automatic checks on the real tool outputs -------------------------
    st = load_state()
    matches = [c for c in CALL_LOG if c["tool"] == "find_matches" and c["status"] == 200]
    claims = [c for c in CALL_LOG if c["tool"] == "submit_claim" and c["status"] == 200]
    if not check("owner agent called find_matches", bool(matches)):
        return
    cands = matches[-1]["result"]["candidates"]
    print("      candidates:", [(c["report_id"], c["score"]) for c in cands])
    check(f"top candidate is the finder's report {st.get('finder_report_id')}",
          bool(cands) and cands[0]["report_id"] == st.get("finder_report_id"))
    secret = st.get("finder_private_detail", "")
    raw = json.dumps([m["result"] for m in matches]).lower()
    check("finder's private detail never appears in search results",
          bool(secret) and secret.lower() not in raw)
    if check("owner agent submitted a claim", bool(claims)):
        c = claims[-1]
        check("claim targets the finder's report",
              c["args"]["found_report_id"] == st.get("finder_report_id"))
        save_state(case_id=c["result"]["case_id"])
        print(f"\nNext: holder's human runs  python scripts/human.py inbox")


def status_step():
    st = load_state()
    t = make_tools(ENV["OWNER_AGENT_TOKEN"], "owner-agent")
    agent = Agent(
        name="owner-agent", model=MODEL, tools=[t["get_case_status"], t["add_case_info"]],
        instructions=("You track your user's Lost Link claim. Check the case status and tell "
                      "your user exactly what to do next. If the holder asked a question, "
                      "say what they asked. " + common_rules()))
    run(agent, f"Any update on my claim {st['case_id']}?")
    s = [c for c in CALL_LOG if c["tool"] == "get_case_status" and c["status"] == 200]
    if s:
        res = s[-1]["result"]
        print("      server says:", res["status"])
        if res["status"] == "approved_for_pickup":
            check("pickup instructions released only after human approval",
                  bool(res.get("pickup_instructions")) and any(
                      d["action"] == "approve" for d in res["human_decisions"]))
            check("item not marked returned before hand-over", res["status"] != "returned")


def misuse_step():
    """Owner agent's own credentials attempting things it must not do."""
    st = load_state()
    h = {"Authorization": f"Bearer {ENV['OWNER_AGENT_TOKEN']}"}
    cid, fid = st.get("case_id", "C-NONE"), st.get("finder_report_id", "F-NONE")
    tries = [
        ("agent calls human approve endpoint", "POST", f"/v1/human/cases/{cid}/decision",
         {"decision": "approve", "pickup_instructions": "anywhere"}, 403),
        ("agent sends human_approved=true in a claim", "POST", "/v1/claims",
         {"lost_report_id": "x", "found_report_id": fid, "claim_message": "mine",
          "request_id": "evil", "human_approved": True}, 422),
        ("agent edits the finder's report", "PATCH", f"/v1/reports/{fid}",
         {"expected_version": 1, "description": "now mine"}, 403),
    ]
    for label, m, path, body, want in tries:
        r = httpx.request(m, BASE + path, json=body, headers=h)
        check(f"{label} -> HTTP {r.status_code} (expected {want})", r.status_code == want)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["finder", "owner", "status", "misuse"])
    ap.add_argument("--say", help="override what the human tells their agent")
    a = ap.parse_args()
    if a.step in ("finder", "owner", "status"):
        MODEL = build_model()
        print(f"[model] provider={PROVIDER} model={os.environ.get('LOSTLINK_MODEL') or PROVIDERS[PROVIDER][2]}")
    {"finder": lambda: finder_step(a.say or FINDER_SAYS),
     "owner": lambda: owner_step(a.say or OWNER_SAYS),
     "status": status_step, "misuse": misuse_step}[a.step]()
