import os
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator
from enum import Enum


DB_PATH = os.getenv("DB_PATH", "helpdesk.db")
API_KEY = os.getenv("API_KEY", "dev-secret-key-change-in-prod")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


class TicketCategory(str, Enum):
    SOFTWARE_ACCESS = "Software/Access Request"
    HARDWARE = "Hardware"
    NETWORK = "Network"
    ACCOUNT = "Account"
    POLICY = "Policy"
    OTHER = "Other"


class TicketPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketStatus(str, Enum):
    NEW = "New"
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: TicketCategory
    priority: TicketPriority
    requester_email: EmailStr
    approver_email: Optional[EmailStr] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title must not be blank")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description must not be blank")
        return v.strip()


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    approver_email: Optional[EmailStr] = None


class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    requester_email: str
    approver_email: Optional[str]
    created_at: str
    updated_at: str


class ConversationLogCreate(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    user_question: str = Field(..., min_length=1, max_length=2000)
    outcome: str = Field(..., pattern="^(Answered|Escalated|Ticket Created|Unanswered)$")
    ticket_id: Optional[str] = None


class ConversationLogResponse(BaseModel):
    log_id: str
    session_id: str
    user_question: str
    outcome: str
    ticket_id: Optional[str]
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id     TEXT PRIMARY KEY,
            title         TEXT NOT NULL,
            description   TEXT NOT NULL,
            category      TEXT NOT NULL,
            priority      TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'New',
            requester_email TEXT NOT NULL,
            approver_email  TEXT,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversation_logs (
            log_id        TEXT PRIMARY KEY,
            session_id    TEXT NOT NULL,
            user_question TEXT NOT NULL,
            outcome       TEXT NOT NULL,
            ticket_id     TEXT,
            timestamp     TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def requires_approval(category: TicketCategory, priority: TicketPriority) -> bool:
    return category == TicketCategory.SOFTWARE_ACCESS or priority in (
        TicketPriority.HIGH,
        TicketPriority.CRITICAL,
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="IT Helpdesk API",
    description=(
        "REST API for the IT Helpdesk AI Agent built with Copilot Studio and Power Automate. "
        "Provides ticket lifecycle management and conversation logging. "
        "All endpoints require an API key via the X-API-Key header."
    ),
    version="1.0.0",
    contact={
        "name": "IT Helpdesk Engineering",
        "email": "helpdesk-eng@company.com",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Service health check",
)
def health_check():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=utc_now(),
    )


@app.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=201,
    tags=["Tickets"],
    summary="Create a new support ticket",
    dependencies=[Depends(validate_api_key)],
)
def create_ticket(payload: TicketCreate):
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now()
    status = (
        TicketStatus.PENDING_APPROVAL
        if requires_approval(payload.category, payload.priority)
        else TicketStatus.NEW
    )

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO tickets
                (ticket_id, title, description, category, priority, status,
                 requester_email, approver_email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                payload.title,
                payload.description,
                payload.category.value,
                payload.priority.value,
                status.value,
                payload.requester_email,
                payload.approver_email,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return TicketResponse(
        ticket_id=ticket_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        status=status,
        requester_email=payload.requester_email,
        approver_email=payload.approver_email,
        created_at=now,
        updated_at=now,
    )


@app.get(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["Tickets"],
    summary="Get a ticket by ID",
    dependencies=[Depends(validate_api_key)],
)
def get_ticket(ticket_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")

    return TicketResponse(**dict(row))


@app.get(
    "/tickets",
    response_model=List[TicketResponse],
    tags=["Tickets"],
    summary="List tickets, optionally filtered by requester email",
    dependencies=[Depends(validate_api_key)],
)
def list_tickets(
    requester: Optional[str] = Query(
        default=None,
        description="Filter tickets by requester email address",
    ),
    status: Optional[TicketStatus] = Query(
        default=None,
        description="Filter tickets by status",
    ),
    limit: int = Query(default=50, ge=1, le=200),
):
    conn = get_db_connection()
    try:
        query = "SELECT * FROM tickets WHERE 1=1"
        params: list = []
        if requester:
            query += " AND requester_email = ?"
            params.append(requester)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [TicketResponse(**dict(r)) for r in rows]


@app.patch(
    "/tickets/{ticket_id}/status",
    response_model=TicketResponse,
    tags=["Tickets"],
    summary="Update the status of an existing ticket",
    dependencies=[Depends(validate_api_key)],
)
def update_ticket_status(ticket_id: str, payload: TicketStatusUpdate):
    now = utc_now()
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")

        update_fields = {"status": payload.status.value, "updated_at": now}
        if payload.approver_email:
            update_fields["approver_email"] = payload.approver_email

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        conn.execute(
            f"UPDATE tickets SET {set_clause} WHERE ticket_id = ?",
            [*update_fields.values(), ticket_id],
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    finally:
        conn.close()

    return TicketResponse(**dict(row))


@app.post(
    "/conversation-logs",
    response_model=ConversationLogResponse,
    status_code=201,
    tags=["Conversation Logs"],
    summary="Log a conversation turn outcome",
    dependencies=[Depends(validate_api_key)],
)
def create_conversation_log(payload: ConversationLogCreate):
    log_id = str(uuid.uuid4())
    now = utc_now()

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO conversation_logs
                (log_id, session_id, user_question, outcome, ticket_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (log_id, payload.session_id, payload.user_question, payload.outcome, payload.ticket_id, now),
        )
        conn.commit()
    finally:
        conn.close()

    return ConversationLogResponse(
        log_id=log_id,
        session_id=payload.session_id,
        user_question=payload.user_question,
        outcome=payload.outcome,
        ticket_id=payload.ticket_id,
        timestamp=now,
    )


@app.get(
    "/conversation-logs",
    response_model=List[ConversationLogResponse],
    tags=["Conversation Logs"],
    summary="Retrieve conversation logs, optionally filtered by session",
    dependencies=[Depends(validate_api_key)],
)
def list_conversation_logs(
    session_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    conn = get_db_connection()
    try:
        query = "SELECT * FROM conversation_logs WHERE 1=1"
        params: list = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [ConversationLogResponse(**dict(r)) for r in rows]
