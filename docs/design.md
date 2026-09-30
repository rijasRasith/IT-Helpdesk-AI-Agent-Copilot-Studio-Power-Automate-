# System Design — IT Helpdesk AI Agent

## Scope

The IT Helpdesk AI Agent handles two types of employee interactions:

1. **Knowledge queries** — Questions answered directly from the SharePoint document library using Retrieval-Augmented Generation (RAG). Answers include document citations.
2. **Actionable requests** — Structured workflows that create, track, or escalate support tickets.

### In Scope

- IT policy and procedure questions (VPN, MFA, passwords, Wi-Fi, hardware, software)
- Onboarding and offboarding checklist queries
- Ticket creation, status lookup, and escalation
- Human-in-the-loop approval for software/access requests and high-priority incidents
- Conversation outcome logging for analytics

### Out of Scope

- HR queries (payroll, benefits, leave)
- Finance and procurement outside software/hardware requests
- Any personally identifiable information beyond requester email
- Questions where the answer cannot be sourced from the knowledge base (agent says so explicitly)

---

## Component Responsibilities

| Component | Role |
|-----------|------|
| Copilot Studio Agent | Conversational interface, topic orchestration, RAG over SharePoint |
| SharePoint "IT Help Center" | Authoritative policy and procedure document store |
| Power Automate Flows | Business logic execution, Dataverse writes, approval routing, notifications |
| FastAPI REST API | Ticket CRUD, input validation, OpenAPI spec for Custom Connector import |
| Dataverse | Persistent ticket and conversation log storage |
| Power BI | Operational monitoring and KB gap analysis |

---

## Data Flow

```
1. User sends a message in Teams / Web Chat
2. Copilot Studio evaluates intent against defined topics
3. If a topic matches → structured conversation flow executes
4. If no topic matches → SharePoint knowledge source is searched (RAG)
5. If RAG answers → response + citation returned
6. If RAG cannot answer → fallback: offer to create a ticket
7. Ticket creation / status actions → Power Automate flow → FastAPI → SQLite/Dataverse
8. Approval-required tickets → Approvals action → manager notified → ticket updated → requester notified
9. Each conversation turn → Log Conversation flow → ConversationLog table
10. Power BI reads Ticket + ConversationLog tables for dashboard
```

---

## Security Design

- Agent is restricted to IT and policy topics via system instructions.
- API endpoints require an API key via HTTP header; keys are stored as environment variables, never in code.
- Dataverse row-level security restricts users to their own tickets.
- The agent explicitly refuses prompt injection attempts ("ignore your instructions").
- No sensitive data (passwords, tokens) is collected or stored by the agent.

---

## Dataverse Schema

### Ticket Table

| Column | Type | Notes |
|--------|------|-------|
| ticket_id | Text (PK, auto) | Format: TKT-XXXXXXXX |
| title | Text | Max 200 chars |
| description | Text | Max 2000 chars |
| category | Choice | Software/Access, Hardware, Network, Account, Policy, Other |
| priority | Choice | Low, Medium, High, Critical |
| status | Choice | New, Pending Approval, Approved, Rejected, In Progress, Resolved |
| requester_email | Email | Validated email address |
| approver_email | Email | Optional; set for approval-path tickets |
| created_at | DateTime | UTC ISO-8601 |
| updated_at | DateTime | UTC ISO-8601 |

### ConversationLog Table

| Column | Type | Notes |
|--------|------|-------|
| log_id | Text (PK, UUID) | |
| session_id | Text | Copilot Studio conversation ID |
| user_question | Text | Raw question text |
| outcome | Choice | Answered, Escalated, Ticket Created, Unanswered |
| ticket_id | Text (FK) | Nullable; set when a ticket was created |
| timestamp | DateTime | UTC ISO-8601 |

---

## Approval Logic

```
IF category == "Software/Access Request" OR priority IN ("High", "Critical"):
    status = "Pending Approval"
    Send Approvals action to approver_email
    IF Approved:
        status = "Approved"
        Notify requester (email / Teams adaptive card)
    IF Rejected:
        status = "Rejected"
        Notify requester with rejection reason
ELSE:
    status = "New"
```

---

## SharePoint Knowledge Base — Document List

| Document | Key Content |
|----------|-------------|
| VPN Setup Guide | Installation, configuration, troubleshooting |
| Password Reset Policy | Self-service reset steps, lockout thresholds |
| Software Request Policy | Approved vendors, request process, approval matrix |
| Laptop Replacement Policy | Eligibility, process, timelines |
| Wi-Fi Troubleshooting | Corporate networks, BYOD policy, common fixes |
| MFA Setup Guide | Authenticator app setup, backup codes, device registration |
| Data Handling Policy | Classification tiers, storage rules, sharing restrictions |
| Onboarding Checklist | Day 1 access provisioning, equipment, account setup |
| Offboarding Procedure | Access revocation, equipment return, data handover |
| Remote Work Policy | Acceptable use, VPN requirements, security baseline |
| Acceptable Use Policy | Permitted and prohibited system usage |
| Incident Reporting Guide | How to report security incidents and outages |

---

## Assumptions and Trade-offs

- SQLite is used for local development to avoid cloud dependency during initial build; Dataverse is the production target.
- The trial Copilot Studio environment supports testing in the test chat panel but not publishing; all demo evidence will be captured via screen recording.
- FastAPI's auto-generated OpenAPI spec is used directly for Custom Connector import, eliminating the need to maintain a separate spec file.
- Approval emails go to a second user in the same trial tenant acting as the manager persona.
