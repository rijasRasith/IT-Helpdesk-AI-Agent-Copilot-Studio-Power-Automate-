# IT Helpdesk AI Agent

An end-to-end IT helpdesk assistant built on Microsoft Copilot Studio and Power Automate, backed by a custom FastAPI REST API, SharePoint RAG knowledge base, Dataverse storage, and Power BI monitoring.

---

## Architecture

```
Employee (Teams / Web Chat)
        │
        ▼
┌──────────────────────────┐
│   Copilot Studio Agent   │  ← Prompt-engineered instructions, citation behavior
│   "IT Helpdesk Assistant"│
└──────────┬───────────────┘
           │  Topics + Actions
     ┌─────┴──────┐
     │            │
     ▼            ▼
SharePoint    Power Automate Flows
Knowledge     ┌──────────────────────────────────┐
Base (RAG)    │  Flow 1: Create Ticket            │
              │  Flow 2: Get Ticket Status        │
              │  Flow 3: Log Conversation         │
              └──────────┬───────────────────────┘
                         │  HTTP / Custom Connector
                         ▼
              ┌─────────────────────┐
              │  FastAPI REST API   │  ← Hosted on Render / Railway / Azure
              │  POST /tickets      │
              │  GET  /tickets/{id} │
              │  GET  /tickets      │
              │  PATCH /tickets/*/status │
              │  POST /conversation-logs │
              └──────────┬──────────┘
                         │  SQLite (dev) / Dataverse (prod)
                         ▼
              ┌─────────────────────┐
              │  Dataverse          │
              │  • Ticket table     │
              │  • ConversationLog  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Power BI Dashboard │
              │  Resolution rate    │
              │  Escalation rate    │
              │  Tickets by status  │
              └─────────────────────┘
```

### Human-in-the-loop Approval Path

```
Ticket created (Software/Access or High/Critical priority)
        │
        ▼  status = Pending Approval
Power Automate Approval action → Manager email
        │
   ┌────┴────┐
Approved   Rejected
   │           │
status=     status=
Approved    Rejected
   │           │
Email/Teams notification → Requester
```

---

## Repository Structure

```
.
├── api/
│   ├── main.py               # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variable template
│   └── tests/
│       └── test_api.py       # PyTest suite
├── docs/
│   ├── design.md             # System design and scope
│   ├── user-guide.md         # End-user instructions
│   └── configuration.md     # Agent instructions, topics, flow schemas
├── solution/                 # Power Platform solution export (.zip)
├── test-cases.csv            # 28 structured test cases
├── Complete_Implementation_Guide.txt
└── README.md
```

---

## Quick Start — API

### Prerequisites

- Python 3.11+
- pip

### Local Setup

```bash
cd api
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set API_KEY to a strong secret value
uvicorn main:app --reload --port 8000
```

### Interactive Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### Run Tests

```bash
cd api
pytest tests/ -v
```

---

## API Authentication

All endpoints (except `/health`) require the header:

```
X-API-Key: <your-api-key>
```

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/tickets` | Create a support ticket |
| GET | `/tickets/{id}` | Retrieve a ticket by ID |
| GET | `/tickets` | List tickets (filter by `requester`, `status`) |
| PATCH | `/tickets/{id}/status` | Update ticket status |
| POST | `/conversation-logs` | Log a conversation turn |
| GET | `/conversation-logs` | Retrieve conversation logs |

---

## Approval Logic

Tickets are automatically set to **Pending Approval** when:

- `category` is `Software/Access Request`, **or**
- `priority` is `High` or `Critical`

All other tickets start at **New**.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `dev-secret-key-change-in-prod` | API authentication key |
| `DB_PATH` | `helpdesk.db` | SQLite database file path |

---

## Deployment

### Render (Recommended for Demo)

1. Push the `api/` folder to a GitHub repository.
2. Create a new **Web Service** on [render.com](https://render.com).
3. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables: `API_KEY`, `DB_PATH=/tmp/helpdesk.db`
5. Copy the public URL and use it in your Power Automate Custom Connector.

### Power Automate Custom Connector

1. Navigate to Power Automate → Data → Custom Connectors.
2. Import from URL: `https://your-api-url.onrender.com/openapi.json`
3. Set authentication type to **API Key** with header name `X-API-Key`.
4. Test the connector using the built-in test panel.

---

## Copilot Studio Setup Summary

| Setting | Value |
|---------|-------|
| Agent name | IT Helpdesk Assistant |
| Knowledge source | SharePoint site "IT Help Center" |
| Authentication | No auth (internal), or Entra ID SSO |
| Primary language | English (US) |
| Fallback behavior | Apologize + offer to create a ticket |

Topics: Create Ticket, Check Ticket Status, Escalate to Human

---

## Power BI Dashboard Metrics

- Total conversations
- Resolution rate (Answered ÷ total)
- Escalation rate
- Tickets by category and status
- Approval turnaround time
- Unanswered questions list (KB gap analysis)

---

## Limitations

- Trial Copilot Studio environments do not allow publishing to production channels; demos should use the built-in test chat panel or a screen recording.
- Custom connectors and Dataverse require premium Power Automate licensing in production.
- SQLite is used for local development; switch to Dataverse or PostgreSQL for production.

---

## License

MIT
