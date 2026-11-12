"""Local-only UI bridge to a fresh, real Lost Link HTTP service.

Each launch/reset starts a disposable database and separate agent/human
credentials. No existing project database or secrets are read. The bridge
represents scripted demo clients; the human buttons are manual role switching,
not a production account or authentication system.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).resolve().parent / "web"


def public(value):
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k not in {
            "private_detail", "your_private_detail", "claim_message", "follow_up_info",
            "Authorization", "X-Human-Token"}}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value


def demo_date():
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


class Bridge:
    def __init__(self):
        self.process = None
        self.temp = None
        self.lock = asyncio.Lock()

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=4)
            self.process = None
        if self.temp is not None:
            self.temp.cleanup()
            self.temp = None

    def start(self):
        self.stop()
        self.temp = tempfile.TemporaryDirectory(prefix="lost-link-dashboard-")
        folder = Path(self.temp.name)
        self.credentials = {k: secrets.token_urlsafe(24) for k in ("finder", "owner", "human")}
        secret_file = folder / "credentials.json"
        secret_file.write_text(json.dumps({
            "agents": {self.credentials["finder"]: "finder", self.credentials["owner"]: "owner"},
            "humans": {self.credentials["human"]: {"name": "demo-holder", "acts_for": "finder"}},
        }))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        self.events, self.candidates, self.case = [], [], None
        self.lost, self.last_claim = None, None
        self.input = {"category": "flask", "color": "navy", "location": "library",
                      "date": demo_date(), "description": "navy flask"}
        env = {**os.environ, "LOSTLINK_DB": str(folder / "demo.db"),
               "LOSTLINK_SECRETS": str(secret_file)}
        with (folder / "service.log").open("w") as log:
            self.process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "lostlink.server:app", "--host", "127.0.0.1",
                 "--port", str(port), "--no-access-log", "--log-level", "warning"],
                cwd=ROOT, env=env, stdout=log, stderr=log,
            )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.stop()
                raise RuntimeError("Temporary Lost Link service did not start")
            try:
                if httpx.get(self.url + "/openapi.json", timeout=.5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.05)
        else:
            self.stop()
            raise RuntimeError("Temporary service startup timed out")
        seed = [
            ("water bottle", "blue", "Hayden Library", "blue water bottle", "A green cactus sticker near the cap"),
            ("bottle", "blue", "Z Center", "blue water bottle", "A climbing sticker on the bottom"),
            ("thermos", "black", "Hayden Library", "black thermos", "The demo initials AB engraved on the base"),
            ("phone", "black", "Student Center", "black iphone", "A star on the back of the demo phone case"),
            ("keys", "silver", "library", "silver keys", "One key has a blue rubber cap"),
            ("wallet", "brown", "Student Center", "brown leather wallet", "A library card in the demo wallet"),
        ]
        self.found_ids = []
        for i, (category, color, location, description, detail) in enumerate(seed):
            r = httpx.post(self.url + "/v1/reports", headers=self.headers("finder"), json={
                "kind": "found", "category": category, "color": color, "location": location,
                "date": demo_date(), "description": description, "private_detail": detail,
                "request_id": f"seed-{i}",
            }, timeout=4)
            r.raise_for_status()
            self.found_ids.append(r.json()["report_id"])
        self.event("finder", "Found items registered", "The finder agent registered 6 campus samples with the service. Verification clues are stored separately.",
                   "Registered", detail={"registered_reports": self.found_ids})

    def headers(self, actor):
        if actor == "human":
            return {"X-Human-Token": self.credentials["human"]}
        return {"Authorization": "Bearer " + self.credentials[actor]}

    def event(self, actor, title, body, tag="Completed", http=None, detail=None):
        self.events.append({"id": len(self.events) + 1, "actor": actor, "title": title,
                            "body": body, "tag": tag, "at": datetime.now().astimezone().isoformat(),
                            "http": http, "detail": public(detail), "simulated": False})

    async def call(self, actor, method, path, body=None, *, title, note="", expected=200):
        async with httpx.AsyncClient(base_url=self.url, timeout=5) as client:
            r = await client.request(method, path, headers=self.headers(actor), json=body)
        payload = r.json()
        self.event(actor, title, note or "The real Lost Link service returned this response.",
                   "Permission enforced" if expected == 403 else "Completed",
                   http={"method": method, "path": path, "status": r.status_code}, detail=payload)
        if r.status_code != expected:
            raise HTTPException(r.status_code, str(payload.get("detail", "The service could not complete this action")))
        return payload

    async def refresh_case(self):
        if self.case:
            async with httpx.AsyncClient(base_url=self.url, timeout=5) as client:
                r = await client.get(f"/v1/cases/{self.case['case_id']}", headers=self.headers("owner"))
            r.raise_for_status()
            self.case = r.json()

    def snapshot(self, review=None):
        return {"mode": "live", "found_count": len(self.found_ids) - int(bool(self.case and self.case["status"] == "returned")),
                "lost": self.lost, "candidates": self.candidates, "case": self.case,
                "events": self.events, "input": self.input, "review": review}

    async def action(self, command):
        action, review = command.action, None
        if action == "reset":
            await asyncio.to_thread(self.start)
        elif action == "search":
            if self.case:
                raise HTTPException(409, "Reset the demo before starting another recovery.")
            self.input = {k: getattr(command, k) for k in ("category", "color", "location", "description")}
            self.input["date"] = command.date or demo_date()
            self.last_report = {**self.input, "kind": "lost", "request_id": "owner-" + secrets.token_hex(6)}
            self.lost = await self.call("owner", "POST", "/v1/reports", self.last_report,
                                        title="Lost report registered", note="The owner agent submitted a structured report from the user’s description.")
            matched = await self.call("owner", "GET", f"/v1/reports/{self.lost['report_id']}/matches",
                                      title="Candidate search completed", note="The service ranks type, color, location and date, and returns reasons for each lead.")
            self.candidates = matched["candidates"]
        elif action == "claim":
            if not self.lost or command.found_id not in {c["report_id"] for c in self.candidates}:
                raise HTTPException(400, "Choose an item from the current search results.")
            if self.case:
                raise HTTPException(409, "There is already a claim for this session.")
            if not command.message.strip():
                raise HTTPException(422, "Enter a verification clue.")
            self.last_claim = {"lost_report_id": self.lost["report_id"], "found_report_id": command.found_id,
                               "claim_message": command.message, "request_id": "claim-" + secrets.token_hex(6)}
            self.case = await self.call("owner", "POST", "/v1/claims", self.last_claim,
                                       title="Private claim submitted", note="The claim is awaiting human review. Pickup instructions remain locked.")
        elif action == "review":
            self.require_case()
            inbox = await self.call("human", "GET", "/v1/human/inbox", title="Holder opened the review inbox",
                                    note="The holder’s private verification clue is shown only in this review view.")
            review = next(r for r in inbox if r["case_id"] == self.case["case_id"])
        elif action in ("approve", "clarify", "reject"):
            self.require_case()
            decision = {"approve": "approve", "clarify": "need_info", "reject": "reject"}[action]
            if action == "approve" and not command.pickup.strip():
                raise HTTPException(422, "Enter pickup instructions.")
            body = {"decision": decision}
            if action == "approve": body["pickup_instructions"] = command.pickup
            if action == "clarify": body["note"] = command.note or "Please add a detail about the item."
            await self.call("human", "POST", f"/v1/human/cases/{self.case['case_id']}/decision", body,
                            title={"approve": "Holder approved pickup", "clarify": "Holder requested clarification", "reject": "Holder rejected claim"}[action],
                            note={"approve": "The human approved the claim. Pickup instructions are now available to the claimant.", "clarify": body.get("note", ""),
                                  "reject": "This claim did not pass verification. Pickup details remain locked."}[action])
        elif action == "info":
            self.require_case()
            if not command.text.strip(): raise HTTPException(422, "Enter an additional detail.")
            await self.call("owner", "POST", f"/v1/cases/{self.case['case_id']}/info", {"text": command.text},
                            title="Additional detail submitted", note="The owner answered the holder’s question. The claim is awaiting review again.")
        elif action == "returned":
            self.require_case()
            await self.call("human", "POST", f"/v1/human/cases/{self.case['case_id']}/returned",
                            title="Holder confirmed the return", note="The holder confirmed the handoff and both linked item reports are closed.")
        elif action == "misuse":
            self.require_case()
            await self.call("owner", "POST", f"/v1/human/cases/{self.case['case_id']}/decision",
                            {"decision": "approve", "pickup_instructions": "forged"},
                            title="Agent self-approval was blocked", note="The real service refused approval using agent credentials. The case state is unchanged.", expected=403)
        elif action == "repeat":
            if not self.lost: raise HTTPException(400, "Run a search first.")
            r = await self.call("owner", "POST", "/v1/reports", self.last_report,
                                title="Repeated registration reused the original report", note="The same request ID reused the existing report instead of creating a duplicate.")
            if not r["duplicate_request"] or r["report_id"] != self.lost["report_id"]:
                raise HTTPException(500, "Report idempotency check failed.")
            if self.last_claim:
                r = await self.call("owner", "POST", "/v1/claims", self.last_claim,
                                    title="Repeated claim reused the original case", note="The retry did not create another claim.")
                if not r["duplicate_request"] or r["case_id"] != self.case["case_id"]:
                    raise HTTPException(500, "Claim idempotency check failed.")
        elif action == "refresh":
            self.require_case()
            self.case = await self.call("owner", "GET", f"/v1/cases/{self.case['case_id']}",
                                       title="Case status checked", note="The owner agent read the current case state from the service.")
        else:
            raise HTTPException(400, "Unsupported action.")
        await self.refresh_case()
        return self.snapshot(review)

    def require_case(self):
        if not self.case: raise HTTPException(400, "Submit a claim first.")


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str
    category: str = Field(default="flask", max_length=80)
    color: str = Field(default="navy", max_length=80)
    location: str = Field(default="library", max_length=150)
    description: str = Field(default="navy flask", max_length=300)
    date: str | None = None
    found_id: str = Field(default="", max_length=80)
    message: str = Field(default="", max_length=1000)
    note: str = Field(default="", max_length=300)
    text: str = Field(default="", max_length=1000)
    pickup: str = Field(default="", max_length=300)


@asynccontextmanager
async def lifespan(app):
    bridge = Bridge()
    try:
        await asyncio.to_thread(bridge.start)
        app.state.bridge = bridge
        yield
    finally:
        await asyncio.to_thread(bridge.stop)


app = FastAPI(title="Lost Link local demo dashboard", lifespan=lifespan)


@app.middleware("http")
async def local_only(request: Request, call_next):
    if request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "This synthetic-data demo is loopback-only."}, status_code=403)
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Cross-origin demo actions are not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/demo/state")
async def state():
    return app.state.bridge.snapshot()


@app.post("/demo/action")
async def action(body: Command):
    async with app.state.bridge.lock:
        return await app.state.bridge.action(body)


@app.get("/")
async def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="dashboard-assets")
