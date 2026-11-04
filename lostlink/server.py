"""
Lost Link – shared lost-and-found service for personal AI agents.

Run:  uvicorn lostlink.server:app --port 8000

Agent-facing endpoints (Bearer <agent token>):
    POST /v1/reports                    register_report
    PATCH /v1/reports/{id}              update own report (optimistic version check)
    GET  /v1/reports/{id}/matches       find_matches   (only for your own lost report)
    POST /v1/claims                     submit_claim
    GET  /v1/cases/{id}                 get_case_status (parties only)
    POST /v1/cases/{id}/info            answer a clarification request

Human-only endpoints (X-Human-Token, never given to agents):
    GET  /v1/human/inbox                claims on reports this human holds
    POST /v1/human/cases/{id}/decision  approve | reject | need_info
    POST /v1/human/cases/{id}/returned  confirm the physical hand-over

Every request is written to the audit_log table and echoed to the terminal,
which is the execution evidence shown in the demo video.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from . import matching

# ---------------------------------------------------------------------------
# Configuration: DB path and the secrets file (tokens -> principals)
# ---------------------------------------------------------------------------
DB_PATH = os.environ.get("LOSTLINK_DB", "lostlink.db")
SECRETS_PATH = os.environ.get("LOSTLINK_SECRETS", "secrets.json")

log = logging.getLogger("lostlink")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    datefmt="%H:%M:%S")


def load_secrets() -> dict:
    """secrets.json = {"agents": {token: agent_id},
                       "humans": {token: {"name":..., "acts_for": agent_id}}}"""
    with open(SECRETS_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Database (SQLite; one process, so a lock + BEGIN IMMEDIATE is enough to
# make "check then write" steps atomic – e.g. the single-approval rule)
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY, kind TEXT NOT NULL, owner_agent TEXT NOT NULL,
    category TEXT, color TEXT, brand TEXT, location TEXT, date TEXT,
    description TEXT, private_detail TEXT,          -- never returned to agents
    status TEXT NOT NULL DEFAULT 'open', version INTEGER NOT NULL DEFAULT 1,
    request_id TEXT, created_at TEXT,
    UNIQUE (owner_agent, request_id)                -- idempotent retries
);
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY, lost_report_id TEXT, found_report_id TEXT,
    claimant_agent TEXT, holder_agent TEXT, claim_message TEXT,
    status TEXT NOT NULL, clarification_request TEXT, pickup_instructions TEXT,
    request_id TEXT, created_at TEXT, updated_at TEXT,
    UNIQUE (claimant_agent, request_id)
);
CREATE TABLE IF NOT EXISTS case_messages (
    case_id TEXT, author TEXT, text TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS human_actions (
    case_id TEXT, human TEXT, action TEXT, note TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS audit_log (
    at TEXT, principal TEXT, method TEXT, path TEXT, status INTEGER);
"""

_lock = threading.Lock()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(3).upper()}"


# ---------------------------------------------------------------------------
# Auth: who is calling?
# ---------------------------------------------------------------------------
def agent_principal(request: Request,
                    authorization: str = Header(default="")) -> str:
    """Resolve a Bearer token to an agent id; 401 otherwise."""
    token = authorization.removeprefix("Bearer ").strip()
    agent = load_secrets()["agents"].get(token)
    if not agent:
        raise HTTPException(401, "unknown agent token")
    request.state.principal = agent
    return agent


def human_principal(request: Request,
                    x_human_token: str = Header(default=""),
                    authorization: str = Header(default="")) -> dict:
    """Resolve the human operator session. Agent tokens are NOT accepted here,
    so an agent cannot approve its own pickup."""
    sec = load_secrets()
    human = sec["humans"].get(x_human_token)
    if not human:
        # Label the refused caller in the audit log if it was an agent.
        agent = sec["agents"].get(authorization.removeprefix("Bearer ").strip())
        request.state.principal = agent or "anonymous"
        raise HTTPException(403, "human session required for this action")
    request.state.principal = f"human:{human['name']}"
    return human


# ---------------------------------------------------------------------------
# Request models. extra="forbid" means an agent that sends e.g.
# {"human_approved": true} gets a 422 instead of silently being ignored.
# ---------------------------------------------------------------------------
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportIn(Strict):
    kind: Literal["lost", "found"]
    category: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    location: Optional[str] = None
    date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD, or null if unknown")
    description: str
    private_detail: Optional[str] = Field(
        None, description="Verification detail; stored, never shown in search")
    request_id: str = Field(..., description="Client-chosen id; retries reuse it")


class ReportPatch(Strict):
    expected_version: int
    category: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    location: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None


class ClaimIn(Strict):
    lost_report_id: str
    found_report_id: str
    claim_message: str = Field(..., description="Private details the owner remembers")
    request_id: str


class InfoIn(Strict):
    text: str


class DecisionIn(Strict):
    decision: Literal["approve", "reject", "need_info"]
    note: Optional[str] = None
    pickup_instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# App + audit middleware
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app):
    init_db()  # create tables on startup
    yield


app = FastAPI(title="Lost Link", version="0.1-mvp", lifespan=lifespan)


@app.middleware("http")
async def audit(request: Request, call_next):
    """Log principal, method, path and status for every call."""
    request.state.principal = "anonymous"
    response = await call_next(request)
    p = request.state.principal
    log.info(f"[audit] {p:<14} {request.method:<5} {request.url.path} -> {response.status_code}")
    conn = get_db()
    conn.execute("INSERT INTO audit_log VALUES (?,?,?,?,?)",
                 (now(), p, request.method, request.url.path, response.status_code))
    conn.close()
    return response


def public_view(r: sqlite3.Row) -> dict:
    """Fields any authorized agent may see. Excludes private_detail and owner."""
    return {k: r[k] for k in ("report_id", "kind", "category", "color", "brand",
                              "location", "date", "description", "status", "version")}


def _get_report(conn, report_id: str) -> sqlite3.Row:
    r = conn.execute("SELECT * FROM reports WHERE report_id=?", (report_id,)).fetchone()
    if not r:
        raise HTTPException(404, "report not found")
    return r


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------
@app.post("/v1/reports")
def register_report(body: ReportIn, agent: str = Depends(agent_principal)):
    with _lock:
        conn = get_db()
        # Idempotency: same agent + same request_id returns the original record.
        old = conn.execute("SELECT * FROM reports WHERE owner_agent=? AND request_id=?",
                           (agent, body.request_id)).fetchone()
        if old:
            return {"report_id": old["report_id"], "version": old["version"],
                    "duplicate_request": True}
        rid = new_id("L" if body.kind == "lost" else "F")
        conn.execute(
            """INSERT INTO reports (report_id, kind, owner_agent, category, color, brand,
               location, date, description, private_detail, request_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, body.kind, agent, body.category, body.color, body.brand, body.location,
             body.date, body.description, body.private_detail, body.request_id, now()))
        conn.close()
    return {"report_id": rid, "version": 1, "duplicate_request": False}


@app.patch("/v1/reports/{report_id}")
def update_report(report_id: str, body: ReportPatch, agent: str = Depends(agent_principal)):
    with _lock:
        conn = get_db()
        r = _get_report(conn, report_id)
        if r["owner_agent"] != agent:
            raise HTTPException(403, "you can only modify your own reports")
        if r["version"] != body.expected_version:
            raise HTTPException(409, f"stale version: current is {r['version']}, re-read first")
        changes = body.model_dump(exclude={"expected_version"}, exclude_none=True)
        sets = ", ".join(f"{k}=?" for k in changes) + (", " if changes else "")
        conn.execute(f"UPDATE reports SET {sets}version=version+1 WHERE report_id=?",
                     (*changes.values(), report_id))
        conn.close()
    return {"report_id": report_id, "version": r["version"] + 1}


@app.get("/v1/reports/{report_id}/matches")
def find_matches(report_id: str, limit: int = 3, agent: str = Depends(agent_principal)):
    conn = get_db()
    lost = _get_report(conn, report_id)
    if lost["owner_agent"] != agent:
        raise HTTPException(403, "you can only search for your own lost report")
    if lost["kind"] != "lost":
        raise HTTPException(400, "matches are computed for lost reports")
    founds = [public_view(r) for r in conn.execute(
        "SELECT * FROM reports WHERE kind='found' AND status='open' AND owner_agent!=?",
        (agent,))]
    conn.close()
    ranked = matching.rank_alias(public_view(lost), founds, limit=max(1, min(limit, 5)))
    by_id = {f["report_id"]: f for f in founds}
    return {
        "lost_report_id": report_id,
        "candidates": [{**c, "found_report": by_id[c["report_id"]]} for c in ranked],
        "missing": matching.missing_fields(public_view(lost)),
        "note": ("A candidate is only worth checking; ownership is verified by the "
                 "holder using private details. Submit a claim to proceed."),
    }


@app.post("/v1/claims")
def submit_claim(body: ClaimIn, agent: str = Depends(agent_principal)):
    with _lock:
        conn = get_db()
        old = conn.execute("SELECT * FROM cases WHERE claimant_agent=? AND request_id=?",
                           (agent, body.request_id)).fetchone()
        if old:
            return {"case_id": old["case_id"], "status": old["status"],
                    "duplicate_request": True}
        lost = _get_report(conn, body.lost_report_id)
        found = _get_report(conn, body.found_report_id)
        if lost["owner_agent"] != agent or lost["kind"] != "lost":
            raise HTTPException(403, "claims must reference your own lost report")
        if found["kind"] != "found" or found["status"] != "open":
            raise HTTPException(409, "found report is not open for claims")
        cid = new_id("C")
        conn.execute(
            """INSERT INTO cases (case_id, lost_report_id, found_report_id, claimant_agent,
               holder_agent, claim_message, status, request_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,'submitted',?,?,?)""",
            (cid, lost["report_id"], found["report_id"], agent, found["owner_agent"],
             body.claim_message, body.request_id, now(), now()))
        conn.close()
    return {"case_id": cid, "status": "submitted", "duplicate_request": False}


@app.get("/v1/cases/{case_id}")
def get_case_status(case_id: str, agent: str = Depends(agent_principal)):
    conn = get_db()
    c = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if not c:
        raise HTTPException(404, "case not found")
    if agent not in (c["claimant_agent"], c["holder_agent"]):
        raise HTTPException(403, "only the parties to a case can read it")
    history = [dict(h) for h in conn.execute(
        "SELECT action, note, at FROM human_actions WHERE case_id=? ORDER BY at", (case_id,))]
    conn.close()
    out = {"case_id": case_id, "status": c["status"],
           "found_report_id": c["found_report_id"],
           "clarification_request": c["clarification_request"],
           "human_decisions": history}
    # Pickup instructions are released only after a human approved the pickup.
    if c["status"] in ("approved_for_pickup", "returned"):
        out["pickup_instructions"] = c["pickup_instructions"]
    return out


@app.post("/v1/cases/{case_id}/info")
def add_case_info(case_id: str, body: InfoIn, agent: str = Depends(agent_principal)):
    with _lock:
        conn = get_db()
        c = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if not c or c["claimant_agent"] != agent:
            raise HTTPException(403, "only the claimant can add information")
        if c["status"] != "needs_clarification":
            raise HTTPException(409, f"case is {c['status']}, no clarification pending")
        conn.execute("INSERT INTO case_messages VALUES (?,?,?,?)", (case_id, agent, body.text, now()))
        conn.execute("UPDATE cases SET status='submitted', updated_at=? WHERE case_id=?",
                     (now(), case_id))
        conn.close()
    return {"case_id": case_id, "status": "submitted"}


# ---------------------------------------------------------------------------
# Human endpoints (holder's operator)
# ---------------------------------------------------------------------------
@app.get("/v1/human/inbox")
def human_inbox(human: dict = Depends(human_principal)):
    """Claims on reports held by this human's agent, with the private detail
    next to the claimant's message so the human can compare them."""
    conn = get_db()
    rows = conn.execute(
        """SELECT c.*, r.description AS found_description, r.private_detail
           FROM cases c JOIN reports r ON r.report_id=c.found_report_id
           WHERE c.holder_agent=? ORDER BY c.created_at""", (human["acts_for"],)).fetchall()
    out = []
    for c in rows:
        msgs = [m["text"] for m in conn.execute(
            "SELECT text FROM case_messages WHERE case_id=? ORDER BY at", (c["case_id"],))]
        out.append({"case_id": c["case_id"], "status": c["status"],
                    "found_report_id": c["found_report_id"],
                    "found_description": c["found_description"],
                    "your_private_detail": c["private_detail"],
                    "claim_message": c["claim_message"], "follow_up_info": msgs})
    conn.close()
    return out


def _holder_case(conn, case_id: str, human: dict) -> sqlite3.Row:
    c = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if not c:
        raise HTTPException(404, "case not found")
    if c["holder_agent"] != human["acts_for"]:
        raise HTTPException(403, "only the holder's human can decide this case")
    return c


@app.post("/v1/human/cases/{case_id}/decision")
def human_decision(case_id: str, body: DecisionIn, human: dict = Depends(human_principal)):
    with _lock:
        conn = get_db()
        conn.execute("BEGIN IMMEDIATE")
        try:
            c = _holder_case(conn, case_id, human)
            if c["status"] not in ("submitted", "needs_clarification"):
                raise HTTPException(409, f"case is already {c['status']}")
            if body.decision == "approve":
                # Single-approval rule: one live approval per found report.
                other = conn.execute(
                    """SELECT case_id FROM cases WHERE found_report_id=? AND case_id!=?
                       AND status IN ('approved_for_pickup','returned')""",
                    (c["found_report_id"], case_id)).fetchone()
                if other:
                    raise HTTPException(409, f"found report already approved in {other['case_id']}")
                if not body.pickup_instructions:
                    raise HTTPException(422, "pickup_instructions required to approve")
                conn.execute("""UPDATE cases SET status='approved_for_pickup',
                                pickup_instructions=?, updated_at=? WHERE case_id=?""",
                             (body.pickup_instructions, now(), case_id))
            elif body.decision == "reject":
                conn.execute("UPDATE cases SET status='rejected', updated_at=? WHERE case_id=?",
                             (now(), case_id))
            else:
                conn.execute("""UPDATE cases SET status='needs_clarification',
                                clarification_request=?, updated_at=? WHERE case_id=?""",
                             (body.note or "Please describe the item in more detail.", now(), case_id))
            conn.execute("INSERT INTO human_actions VALUES (?,?,?,?,?)",
                         (case_id, human["name"], body.decision, body.note, now()))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
    return {"case_id": case_id, "decision": body.decision}


@app.post("/v1/human/cases/{case_id}/returned")
def human_returned(case_id: str, human: dict = Depends(human_principal)):
    with _lock:
        conn = get_db()
        c = _holder_case(conn, case_id, human)
        if c["status"] != "approved_for_pickup":
            raise HTTPException(409, "only an approved pickup can be marked returned")
        conn.execute("UPDATE cases SET status='returned', updated_at=? WHERE case_id=?",
                     (now(), case_id))
        conn.execute("UPDATE reports SET status='closed' WHERE report_id IN (?,?)",
                     (c["lost_report_id"], c["found_report_id"]))
        conn.execute("INSERT INTO human_actions VALUES (?,?,?,?,?)",
                     (case_id, human["name"], "returned", None, now()))
        conn.close()
    return {"case_id": case_id, "status": "returned"}
