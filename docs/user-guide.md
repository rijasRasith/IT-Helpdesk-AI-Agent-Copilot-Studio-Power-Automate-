# User Guide — IT Helpdesk Assistant

## What Is the IT Helpdesk Assistant?

The IT Helpdesk Assistant is an AI-powered chat agent available in Microsoft Teams. It can answer IT policy questions instantly, help you raise support tickets, and check the status of existing tickets — all without waiting for a human agent.

---

## How to Access It

1. Open Microsoft Teams.
2. In the left sidebar, click **Apps**.
3. Search for **IT Helpdesk Assistant**.
4. Click **Open** or **Chat**.

The agent is also available at the embedded web chat link shared by your IT team.

---

## What It Can Do

### Answer IT Questions

Ask questions like:

- *"How do I set up the VPN?"*
- *"What is the password reset policy?"*
- *"How do I register my phone for MFA?"*
- *"What software is approved for data storage?"*

The agent answers from the official IT policy documents and includes a reference to the source document. If it cannot find an answer, it will tell you and offer to raise a ticket.

### Raise a Support Ticket

Say something like:

- *"My laptop keyboard isn't working"*
- *"I need Adobe Acrobat installed"*
- *"Wi-Fi keeps dropping in the meeting room"*

The agent will ask you for:
1. A short title for the issue
2. A description of what is happening
3. The category (Hardware, Network, Software/Access Request, etc.)
4. The urgency level (Low, Medium, High, Critical)

It will then create a ticket and give you a **Ticket ID** (e.g. `TKT-3FA8B2C1`). Keep this ID to check your ticket later.

### Check a Ticket's Status

Say: *"What is the status of ticket TKT-3FA8B2C1?"*

The agent will return the current status:

| Status | Meaning |
|--------|---------|
| New | Received and queued for an agent |
| Pending Approval | Waiting for manager approval (software/access or high priority) |
| Approved | Approved; IT is processing the request |
| Rejected | Request was not approved; see rejection note in email |
| In Progress | IT is actively working on the issue |
| Resolved | The issue has been resolved |

### Escalate to a Human Agent

If you prefer to speak to a person, or if the agent cannot help, say:

- *"I need to speak to someone"*
- *"Escalate this"*
- *"This is urgent"*

The agent will acknowledge the escalation and submit a ticket with escalation priority.

---

## What It Cannot Do

- Answer questions outside of IT and company policy (e.g., payroll, HR, cafeteria menus).
- Access or modify your files or accounts directly.
- Approve its own tickets.
- Invent policy — if the answer is not in the official documentation, it will say so.

---

## Tips for Best Results

- **Be specific.** Instead of "it's broken," say "my laptop screen flickers when on battery power."
- **One topic at a time.** The agent handles one issue per conversation turn most accurately.
- **Multi-turn context works.** After asking about a VPN issue, you can say "raise a ticket for that" and the agent will use the earlier context.
- **Restart the conversation** if the agent seems confused — it starts fresh each session.

---

## Privacy

The agent stores your email address and the text of your request to track your ticket. It does not store passwords, credentials, or sensitive personal information. All data is held in the company's Microsoft 365 tenant and governed by the company's data handling policy.

---

## Contact

If the agent is unavailable or you have feedback, contact the IT team directly at **it-support@company.com** or call extension **4400**.
