# ai-generated: 90% - I implemented the service from the published contract and kept the decision set explicit in the code path

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

APP_TZ = ZoneInfo("Europe/Warsaw")
DB_PATH = os.environ.get("SVCDESK_DB", "/data/svcdesk.db")
TEST_CLOCK_HEADER = "X-Test-Clock"


class SvcDeskError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def init_db() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def to_rfc3339(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_request_time(request: Request) -> datetime:
    if os.environ.get("SVCDESK_TEST_CLOCK", "").lower() not in {"1", "true"}:
        return datetime.now(timezone.utc)
    value = request.headers.get(TEST_CLOCK_HEADER)
    if value is None:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SvcDeskError(400, "validation", "X-Test-Clock is malformed") from exc
    if parsed.tzinfo is None:
        raise SvcDeskError(400, "validation", "X-Test-Clock is malformed")
    return parsed.astimezone(timezone.utc)


def is_business_window(local_dt: datetime) -> bool:
    if local_dt.weekday() >= 5:
        return False
    start = datetime.combine(local_dt.date(), time(8, 0), tzinfo=local_dt.tzinfo)
    end = datetime.combine(local_dt.date(), time(16, 0), tzinfo=local_dt.tzinfo)
    return start <= local_dt < end


def next_business_start(local_dt: datetime) -> datetime:
    current = local_dt.date()
    while True:
        if current.weekday() < 5:
            start = datetime.combine(current, time(8, 0), tzinfo=local_dt.tzinfo)
            if local_dt < start:
                return start
            return datetime.combine(current + timedelta(days=1), time(8, 0), tzinfo=local_dt.tzinfo) if local_dt >= start else start
        current += timedelta(days=1)


def business_due(start_utc: datetime, target_seconds: int) -> datetime:
    remaining = target_seconds
    current = start_utc.astimezone(APP_TZ)

    while True:
        if current.weekday() >= 5:
            current = datetime.combine(current.date() + timedelta(days=1), time(8, 0), tzinfo=current.tzinfo)
            while current.weekday() >= 5:
                current += timedelta(days=1)
            continue
        if current.time() < time(8, 0):
            current = datetime.combine(current.date(), time(8, 0), tzinfo=current.tzinfo)
            continue
        if current.time() >= time(16, 0):
            current = datetime.combine(current.date() + timedelta(days=1), time(8, 0), tzinfo=current.tzinfo)
            while current.weekday() >= 5:
                current += timedelta(days=1)
            continue

        day_end = datetime.combine(current.date(), time(16, 0), tzinfo=current.tzinfo)
        available = (day_end - current).total_seconds()
        if remaining <= available:
            return (current + timedelta(seconds=remaining)).astimezone(timezone.utc)
        remaining -= available
        current = datetime.combine(current.date() + timedelta(days=1), time(8, 0), tzinfo=current.tzinfo)
        while current.weekday() >= 5:
            current += timedelta(days=1)


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    matrix = {
        (1, 1): "P1",
        (1, 2): "P2",
        (1, 3): "P3",
        (2, 1): "P2",
        (2, 2): "P3",
        (2, 3): "P4",
        (3, 1): "P3",
        (3, 2): "P4",
        (3, 3): "P4",
    }
    result = matrix[(impact, urgency)]
    if vip and result in {"P3", "P4"}:
        return "P2"
    return result


def priority_target_seconds(priority: str, is_ack: bool) -> int:
    table = {
        "P1": (900, 14400),
        "P2": (3600, 28800),
        "P3": (14400, 86400),
        "P4": (28800, 259200),
    }
    ack, resolve = table[priority]
    return ack if is_ack else resolve


def build_sla(created_at: datetime, priority: str) -> dict[str, str]:
    ack_due = business_due(created_at, priority_target_seconds(priority, True))
    resolve_due = business_due(created_at, priority_target_seconds(priority, False))
    return {"ack_due_at": to_rfc3339(ack_due), "resolve_due_at": to_rfc3339(resolve_due)}


def parse_ticket_body(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SvcDeskError(422, "validation", "request body must be a JSON object")

    title = raw.get("title")
    if not isinstance(title, str) or len(title.strip()) == 0 or len(title) > 200:
        raise SvcDeskError(422, "validation", "title is required")

    description = raw.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str) or len(description) > 4000:
        raise SvcDeskError(422, "validation", "description is invalid")

    reporter = raw.get("reporter", {})
    if not isinstance(reporter, dict):
        raise SvcDeskError(422, "validation", "reporter is required")

    name = reporter.get("name")
    if not isinstance(name, str) or len(name.strip()) == 0 or len(name) > 100:
        raise SvcDeskError(422, "validation", "reporter.name is required")

    email = reporter.get("email")
    if email is not None and (not isinstance(email, str) or len(email) > 255):
        raise SvcDeskError(422, "validation", "reporter.email is invalid")

    vip = reporter.get("vip", False)
    if not isinstance(vip, bool):
        raise SvcDeskError(422, "validation", "reporter.vip is invalid")

    impact = raw.get("impact")
    urgency = raw.get("urgency")
    if not isinstance(impact, int) or isinstance(impact, bool) or impact not in {1, 2, 3}:
        raise SvcDeskError(422, "validation", "impact is invalid")
    if not isinstance(urgency, int) or isinstance(urgency, bool) or urgency not in {1, 2, 3}:
        raise SvcDeskError(422, "validation", "urgency is invalid")

    related_to = raw.get("related_to")
    if related_to is not None and (not isinstance(related_to, str) or related_to == ""):
        raise SvcDeskError(422, "validation", "related_to is invalid")

    return {
        "title": title,
        "description": description,
        "reporter": {"name": name, "email": email, "vip": vip},
        "impact": impact,
        "urgency": urgency,
        "related_to": related_to,
    }


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_ticket(ticket_id: str) -> dict[str, Any]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT payload FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise SvcDeskError(404, "not_found", f"ticket {ticket_id} not found")
    return json.loads(row["payload"])


def save_ticket(ticket: dict[str, Any]) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO tickets (id, payload) VALUES (?, ?)",
            (ticket["id"], json.dumps(ticket, separators=(",", ":"))),
        )
        conn.commit()
    finally:
        conn.close()


def assess_breach(ticket: dict[str, Any], now: datetime) -> tuple[bool, bool]:
    ack_due = datetime.fromisoformat(ticket["sla"]["ack_due_at"].replace("Z", "+00:00"))
    resolve_due = datetime.fromisoformat(ticket["sla"]["resolve_due_at"].replace("Z", "+00:00"))

    if ticket.get("acknowledged_at") is not None:
        ack_breached = datetime.fromisoformat(ticket["acknowledged_at"].replace("Z", "+00:00")) > ack_due
    else:
        ack_breached = now > ack_due

    if ticket.get("resolved_at") is not None:
        resolve_breached = datetime.fromisoformat(ticket["resolved_at"].replace("Z", "+00:00")) > resolve_due
    else:
        resolve_breached = now > resolve_due

    return ack_breached, resolve_breached


def paused_for_ticket(ticket: dict[str, Any], now: datetime) -> bool:
    if ticket.get("state") in {"resolved", "closed"}:
        return False
    return not is_business_window(now.astimezone(APP_TZ))


def validate_transition(ticket: dict[str, Any], action: str) -> None:
    state = ticket.get("state")
    if action == "ack":
        if state != "new":
            raise SvcDeskError(409, "invalid_transition", "invalid transition")
        return
    if action == "start":
        if state != "acknowledged":
            raise SvcDeskError(409, "invalid_transition", "invalid transition")
        return
    if action == "resolve":
        if state != "in_progress":
            raise SvcDeskError(409, "invalid_transition", "invalid transition")
        return
    if action == "close":
        if state != "resolved":
            raise SvcDeskError(409, "invalid_transition", "invalid transition")
        return
    if action == "reopen":
        if state == "new":
            raise SvcDeskError(409, "invalid_transition", "invalid transition")
        if state == "resolved":
            return
        if state == "closed":
            raise SvcDeskError(409, "invalid_transition", "closed tickets are immutable")
        raise SvcDeskError(409, "invalid_transition", "invalid transition")


app = FastAPI()


@app.exception_handler(SvcDeskError)
async def svcdesk_error_handler(_, exc: SvcDeskError):
    return error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_, exc: RequestValidationError):
    message = exc.errors()[0]["msg"] if exc.errors() else "invalid request"
    return error_response(422, "validation", message)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return error_response(404, "not_found", "not found")
    if exc.status_code == 405:
        return error_response(405, "method_not_allowed", "method not allowed")
    return error_response(exc.status_code, "error", str(exc.detail))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
async def create_ticket(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise SvcDeskError(422, "validation", "request body must be valid JSON") from exc

    ticket_data = parse_ticket_body(payload)
    now = parse_request_time(request)
    priority = compute_priority(ticket_data["impact"], ticket_data["urgency"], ticket_data["reporter"]["vip"])
    ticket = {
        "id": str(uuid.uuid4()),
        "title": ticket_data["title"],
        "description": ticket_data["description"],
        "reporter": ticket_data["reporter"],
        "impact": ticket_data["impact"],
        "urgency": ticket_data["urgency"],
        "priority": priority,
        "state": "new",
        "created_at": to_rfc3339(now),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": ticket_data["related_to"],
        "sla": build_sla(now, priority),
    }
    save_ticket(ticket)
    return ticket


@app.get("/tickets")
async def list_tickets(state: Optional[str] = Query(default=None), priority: Optional[str] = Query(default=None)) -> list[dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute("SELECT payload FROM tickets").fetchall()
    finally:
        conn.close()
    tickets = [json.loads(r["payload"]) for r in rows]
    if state is not None:
        tickets = [t for t in tickets if t.get("state") == state]
    if priority is not None:
        tickets = [t for t in tickets if t.get("priority") == priority]
    return tickets


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> dict[str, Any]:
    return load_ticket(ticket_id)


@app.get("/tickets/{ticket_id}/sla")
async def sla_for_ticket(ticket_id: str, request: Request) -> dict[str, Any]:
    ticket = load_ticket(ticket_id)
    now = parse_request_time(request)
    ack_breached, resolve_breached = assess_breach(ticket, now)
    return {
        "priority": ticket["priority"],
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused_for_ticket(ticket, now),
    }


def apply_action(ticket_id: str, action: str, request: Request) -> dict[str, Any]:
    ticket = load_ticket(ticket_id)
    now = parse_request_time(request)

    if action == "reopen":
        state = ticket.get("state")
        if state == "resolved":
            resolved_at = datetime.fromisoformat(ticket["resolved_at"].replace("Z", "+00:00"))
            if now > resolved_at + timedelta(days=7):
                raise SvcDeskError(409, "reopen_window_expired", "reopen window expired")
        elif state == "closed":
            raise SvcDeskError(409, "invalid_transition", "closed tickets are immutable")
        else:
            raise SvcDeskError(409, "invalid_transition", "invalid transition")

    validate_transition(ticket, action)

    if action == "ack":
        ticket["state"] = "acknowledged"
        ticket["acknowledged_at"] = to_rfc3339(now)
    elif action == "start":
        ticket["state"] = "in_progress"
    elif action == "resolve":
        ticket["state"] = "resolved"
        ticket["resolved_at"] = to_rfc3339(now)
    elif action == "close":
        ticket["state"] = "closed"
        ticket["closed_at"] = to_rfc3339(now)
    elif action == "reopen":
        ticket["state"] = "in_progress"
        ticket["resolved_at"] = None
        ticket["closed_at"] = None

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/ack")
async def ack(ticket_id: str, request: Request) -> dict[str, Any]:
    return apply_action(ticket_id, "ack", request)


@app.post("/tickets/{ticket_id}/start")
async def start(ticket_id: str, request: Request) -> dict[str, Any]:
    return apply_action(ticket_id, "start", request)


@app.post("/tickets/{ticket_id}/resolve")
async def resolve(ticket_id: str, request: Request) -> dict[str, Any]:
    return apply_action(ticket_id, "resolve", request)


@app.post("/tickets/{ticket_id}/close")
async def close(ticket_id: str, request: Request) -> dict[str, Any]:
    return apply_action(ticket_id, "close", request)


@app.post("/tickets/{ticket_id}/reopen")
async def reopen(ticket_id: str, request: Request) -> dict[str, Any]:
    return apply_action(ticket_id, "reopen", request)


init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("svcdesk.main:app", host="0.0.0.0", port=8080)
