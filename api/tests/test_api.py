import pytest
from fastapi.testclient import TestClient
from main import app, DB_PATH, init_db, API_KEY
import os
import tempfile


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    test_db = str(tmp_path / "test_helpdesk.db")
    monkeypatch.setattr("main.DB_PATH", test_db)
    monkeypatch.setenv("DB_PATH", test_db)
    import main as m
    m.DB_PATH = test_db
    m.init_db()
    yield test_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY}


@pytest.fixture
def bad_headers():
    return {"X-API-Key": "wrong-key"}


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body


def test_create_ticket_success(client, auth_headers):
    payload = {
        "title": "Cannot access VPN",
        "description": "VPN client keeps disconnecting after the latest update",
        "category": "Network",
        "priority": "Medium",
        "requester_email": "employee@company.com",
    }
    response = client.post("/tickets", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["status"] == "New"
    assert body["ticket_id"].startswith("TKT-")


def test_create_ticket_triggers_approval_for_software_request(client, auth_headers):
    payload = {
        "title": "Adobe Acrobat license request",
        "description": "Need Adobe Acrobat Pro for contract document processing",
        "category": "Software/Access Request",
        "priority": "Low",
        "requester_email": "employee@company.com",
    }
    response = client.post("/tickets", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["status"] == "Pending Approval"


def test_create_ticket_triggers_approval_for_high_priority(client, auth_headers):
    payload = {
        "title": "Production server down",
        "description": "The production application server is unresponsive since 14:00",
        "category": "Hardware",
        "priority": "High",
        "requester_email": "ops@company.com",
    }
    response = client.post("/tickets", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["status"] == "Pending Approval"


def test_create_ticket_triggers_approval_for_critical_priority(client, auth_headers):
    payload = {
        "title": "Data breach suspected",
        "description": "Unusual outbound traffic detected from marketing subnet",
        "category": "Network",
        "priority": "Critical",
        "requester_email": "security@company.com",
    }
    response = client.post("/tickets", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["status"] == "Pending Approval"


def test_get_ticket_by_id(client, auth_headers):
    payload = {
        "title": "Laptop keyboard not working",
        "description": "Several keys on the keyboard have stopped responding",
        "category": "Hardware",
        "priority": "Medium",
        "requester_email": "jane.doe@company.com",
    }
    created = client.post("/tickets", json=payload, headers=auth_headers).json()
    ticket_id = created["ticket_id"]

    response = client.get(f"/tickets/{ticket_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket_id
    assert body["requester_email"] == "jane.doe@company.com"


def test_get_ticket_not_found(client, auth_headers):
    response = client.get("/tickets/TKT-NONEXISTENT", headers=auth_headers)
    assert response.status_code == 404


def test_list_tickets_returns_all(client, auth_headers):
    for i in range(3):
        client.post(
            "/tickets",
            json={
                "title": f"Issue number {i + 1}",
                "description": "Description for the test issue that was created",
                "category": "Account",
                "priority": "Low",
                "requester_email": "test@company.com",
            },
            headers=auth_headers,
        )
    response = client.get("/tickets", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_list_tickets_filtered_by_requester(client, auth_headers):
    client.post(
        "/tickets",
        json={
            "title": "Alice specific ticket",
            "description": "This ticket belongs only to Alice in the test suite",
            "category": "Policy",
            "priority": "Low",
            "requester_email": "alice@company.com",
        },
        headers=auth_headers,
    )
    client.post(
        "/tickets",
        json={
            "title": "Bob specific ticket",
            "description": "This ticket belongs only to Bob in the test suite",
            "category": "Policy",
            "priority": "Low",
            "requester_email": "bob@company.com",
        },
        headers=auth_headers,
    )
    response = client.get("/tickets?requester=alice@company.com", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert all(r["requester_email"] == "alice@company.com" for r in results)


def test_update_ticket_status(client, auth_headers):
    created = client.post(
        "/tickets",
        json={
            "title": "MFA token stopped working",
            "description": "Authenticator app stopped generating valid codes today",
            "category": "Account",
            "priority": "Medium",
            "requester_email": "user@company.com",
        },
        headers=auth_headers,
    ).json()
    ticket_id = created["ticket_id"]

    response = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "Resolved"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Resolved"


def test_update_ticket_status_not_found(client, auth_headers):
    response = client.patch(
        "/tickets/TKT-GHOST/status",
        json={"status": "Resolved"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_ticket_missing_api_key(client):
    response = client.post(
        "/tickets",
        json={
            "title": "Unauthorized attempt",
            "description": "Should fail because no API key is provided here",
            "category": "Other",
            "priority": "Low",
            "requester_email": "hacker@evil.com",
        },
    )
    assert response.status_code in (401, 403)


def test_create_ticket_wrong_api_key(client, bad_headers):
    response = client.post(
        "/tickets",
        json={
            "title": "Wrong key attempt",
            "description": "Should fail because the API key is incorrect here",
            "category": "Other",
            "priority": "Low",
            "requester_email": "hacker@evil.com",
        },
        headers=bad_headers,
    )
    assert response.status_code == 403


def test_create_ticket_invalid_category(client, auth_headers):
    response = client.post(
        "/tickets",
        json={
            "title": "Bad category",
            "description": "This request has an invalid category that should fail",
            "category": "NotACategory",
            "priority": "Low",
            "requester_email": "user@company.com",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_ticket_invalid_email(client, auth_headers):
    response = client.post(
        "/tickets",
        json={
            "title": "Bad email format test",
            "description": "This request has an invalid email that should cause failure",
            "category": "Other",
            "priority": "Low",
            "requester_email": "not-an-email",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_conversation_log(client, auth_headers):
    payload = {
        "session_id": "sess-abc123",
        "user_question": "How do I reset my password?",
        "outcome": "Answered",
    }
    response = client.post("/conversation-logs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["session_id"] == "sess-abc123"
    assert body["outcome"] == "Answered"
    assert "log_id" in body


def test_conversation_log_with_ticket_id(client, auth_headers):
    ticket = client.post(
        "/tickets",
        json={
            "title": "Wi-Fi drops in meeting rooms",
            "description": "Wireless connectivity is unreliable in all meeting rooms on floor 3",
            "category": "Network",
            "priority": "Medium",
            "requester_email": "staff@company.com",
        },
        headers=auth_headers,
    ).json()

    payload = {
        "session_id": "sess-xyz456",
        "user_question": "Wi-Fi keeps dropping in the meeting room",
        "outcome": "Ticket Created",
        "ticket_id": ticket["ticket_id"],
    }
    response = client.post("/conversation-logs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["ticket_id"] == ticket["ticket_id"]


def test_conversation_log_invalid_outcome(client, auth_headers):
    payload = {
        "session_id": "sess-bad",
        "user_question": "What is the weather?",
        "outcome": "InvalidOutcome",
    }
    response = client.post("/conversation-logs", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_list_conversation_logs(client, auth_headers):
    for outcome in ["Answered", "Escalated", "Unanswered"]:
        client.post(
            "/conversation-logs",
            json={
                "session_id": "sess-list-test",
                "user_question": f"A question with outcome: {outcome}",
                "outcome": outcome,
            },
            headers=auth_headers,
        )
    response = client.get(
        "/conversation-logs?session_id=sess-list-test", headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
