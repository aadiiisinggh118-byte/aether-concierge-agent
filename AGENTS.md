# 🛡️ Aether Concierge — Agent System Documentation

> **Privacy-First Autonomous Life Guardian**
> Built for the Google x Kaggle 5-Day AI Agents Intensive — Capstone 2026
> Track: **Concierge Agents**
> Model: **Gemini 2.5 Flash** | Framework: **Gradio** | MCP: **HTTP Server (port 8765)**

---

## 🧭 Core Philosophy

> *"Your personal DATA never leaves your machine. Only sanitized operational intent is processed by AI."*

Aether Concierge is built on a two-layer privacy architecture:
- **Layer 1:** All personal data stored locally in JSON/text files — never uploaded to any cloud
- **Layer 2:** Privacy Analyst node automatically redacts PII before any AI processing — Gemini only sees sanitized intent, never raw personal information

---

## 🏗️ Complete System Architecture

```
═══════════════════════════════════════════════════════════════════
                    AETHER CONCIERGE SYSTEM
                    Full Architecture Diagram
═══════════════════════════════════════════════════════════════════

  USER INPUT (Natural Language)
         │
         ▼
  ┌──────────────────────────┐
  │   PRE-FLIGHT             │  ← LOCAL, Zero API calls
  │   SECURITY GATE          │
  │                          │  Banned: sudo rm, format c:,
  │   Scans for dangerous    │  --bypass_rules, eval(), exec(),
  │   commands BEFORE any    │  rm -rf, os.system, subprocess
  │   API call               │
  └──────────────────────────┘
         │ SAFE ✅           │ DANGEROUS ❌
         ▼                   ▼
         │              BLOCK & ALERT
         │              (No API call wasted)
         ▼
  ┌────────────────────────────────────────────────────────────┐
  │                  SINGLE GEMINI 2.5 FLASH API CALL          │
  │                  (1 call = 3x quota savings)               │
  │                                                            │
  │  ┌──────────────────────┐   ┌──────────────────────────┐  │
  │  │  NODE A              │   │  NODE B                  │  │
  │  │  PRIVACY ANALYST     │──▶│  LOGIC ENGINE            │  │
  │  │                      │   │                          │  │
  │  │  • Reads raw input   │   │  • Classifies domain     │  │
  │  │  • Detects PII       │   │    (TASKS/HEALTH/        │  │
  │  │  • Redacts:          │   │     EVENTS/GARDEN)       │  │
  │  │    passwords→[RED]   │   │  • Selects 1 of 16       │  │
  │  │    SSN→[REDACTED]    │   │    action types          │  │
  │  │    banking→[RED]     │   │  • Extracts structured   │  │
  │  │  • Outputs clean     │   │    data as JSON          │  │
  │  │    safe intent       │   │  • Uses conversation     │  │
  │  │                      │   │    context for refs      │  │
  │  └──────────────────────┘   └──────────────────────────┘  │
  │                                                            │
  │  Returns: Single JSON with domain + action + data          │
  └────────────────────────────────────────────────────────────┘
         │ Structured JSON response
         ▼
  ┌──────────────────────────┐
  │   NODE C                 │  ← LOCAL, Zero API calls
  │   PHYSICAL EXECUTOR      │
  │                          │
  │   16 Action Types:       │
  │   TASKS:                 │
  │   • LOG_TASK             │
  │   • COMPLETE_TASK        │  Reads/writes to:
  │   • DELETE_TASK          │  Test_Desktop/
  │   • LIST_TASKS           │  ├── daily_tasks.json
  │   • UPDATE_PRIORITY      │  ├── health_tracker.json
  │   • SEARCH_TASKS         │  ├── events.json
  │   HEALTH:                │  └── garden_planner.json
  │   • LOG_MEDICATION       │
  │   • LOG_APPOINTMENT      │
  │   • LIST_HEALTH          │
  │   EVENTS:                │
  │   • LOG_EVENT            │
  │   • ADD_GUEST            │
  │   • LIST_EVENTS          │
  │   GARDEN:                │
  │   • LOG_PLANT            │
  │   • LOG_GARDEN_TASK      │
  │   • LIST_GARDEN          │
  │   • UNKNOWN              │
  └──────────────────────────┘
         │ Confirmation message
         ▼
  ┌──────────────────────────┐
  │   ANALYTICS LEDGER       │  ← LOCAL CSV only
  │   concierge_analytics    │
  │   .csv                   │  Stores: Timestamp, Domain,
  │                          │  Action, Safe_Input, Result
  │   Used by Guardian for   │  (PII-free — sanitized only)
  │   pattern analysis       │
  └──────────────────────────┘

═══════════════════════════════════════════════════════════════════
           AUTONOMOUS SYSTEMS (Run in Background)
═══════════════════════════════════════════════════════════════════

  ┌────────────────────────────────────────────────────────────┐
  │          GUARDIAN MODE (Background Daemon Thread)          │
  │          Starts automatically when app launches            │
  │          NO user input required — fully autonomous         │
  └────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         CHECK 1         CHECK 2         CHECK 3
      Missed Meds      Overdue Tasks   Events in
      after 10am       2+ days old     next 24hrs
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌──────────────────┐
                    │  RISK ASSESSMENT │
                    │                  │
                    │  LOW    = green  │
                    │  MEDIUM = yellow │
                    │  HIGH   = red    │
                    │  CRITICAL= alert │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │   AUTO DECISION ENGINE   │
                    │                          │
                    │  If misses >= 2:         │
                    │  → Escalate risk         │
                    │  → Send notification     │
                    │  → Monitor every 30min   │
                    │                          │
                    │  If misses >= 3:         │
                    │  → AUTO-CREATE task:     │
                    │    "Schedule doctor"     │
                    │  → Set HIGH priority     │
                    │  → Due in 2 days         │
                    │  → Notify user           │
                    └──────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │  ADAPTIVE MONITORING     │
                    │                          │
                    │  CRITICAL/HIGH → 30 min  │
                    │  MEDIUM        → 45 min  │
                    │  LOW           → 60 min  │
                    └──────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    INTERVENTION PLAN              WINDOWS NOTIFICATIONS
    (Dynamic, auto-generated)      (Real desktop popups)
    • Problems detected            • Missed dose alert
    • Actions taken                • Task overdue alert
    • Recommendations              • Event reminder
    • Next check time              • Auto-action taken

  ┌────────────────────────────────────────────────────────────┐
  │          MCP SERVER (Separate HTTP Process)                │
  │          http://127.0.0.1:8765                             │
  │          Any external agent can connect                    │
  └────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   Tool 1               Tool 2               Tool 3
   GET /get_            GET /check_          GET /get_
   current_             overdue_             medication_
   datetime             tasks                due_today
         │                    │                    │
         ▼                    ▼                    ▼
   Tool 4               Tool 5
   GET /get_            GET /generate_
   upcoming_            daily_briefing
   events               (flagship tool)
```

---

## 🤖 Node A — Privacy Analyst

**Type:** AI Agent (Gemini 2.5 Flash)
**Trigger:** Every user request, before any data processing
**API Calls:** Part of single combined call with Node B

### What It Does

```
RAW INPUT:   "Add task: Pay $5000 from account #4521 to landlord, pw=secret123"
                              │
                    Privacy Analyst scans
                              │
SAFE OUTPUT: "Add task: Pay [REDACTED] from account [REDACTED] to landlord"
```

### PII Categories Detected & Redacted

| Category | Examples | Replaced With |
|----------|---------|---------------|
| Passwords | secret123, mypassword | [REDACTED] |
| Banking | account #4521, routing 0923 | [REDACTED] |
| SSN | 123-45-6789 | [REDACTED] |
| API Keys | sk-abc123, AIza... | [REDACTED] |
| Private paths | C:\Users\secret | [REDACTED_PATH] |

### Key Design Decision

Node A and Node B combined into ONE Gemini API call.
Traditional approach = 2 separate calls.
Our approach = 1 call, half the quota used.

---

## 🧠 Node B — Logic Engine

**Type:** AI Agent (Gemini 2.5 Flash, same call as Node A)
**Purpose:** Strict classification and structured extraction

### Classification Rules

```
User says "urgent" / "important" / "ASAP"  →  priority: HIGH
User says "whenever" / "low priority"       →  priority: LOW
No priority mentioned                        →  priority: MEDIUM (default)

User says "mark that as done"               →  uses conversation context
User says "add to that event"               →  references last event
User says "change its priority"             →  references last task
```

### Output Format (Strict JSON)

```json
{
  "safe_input": "sanitized version of input",
  "domain": "TASKS",
  "action": "LOG_TASK",
  "extracted_data": {
    "title": "Submit Kaggle project",
    "priority": "high",
    "date": "2026-07-06",
    "time": "5:00 PM",
    "people": [],
    "notes": "capstone deadline",
    "quantity": null,
    "search_term": null,
    "task_reference": null
  },
  "user_message": "Got it! I've added Submit Kaggle project as a HIGH priority task due July 6."
}
```

---

## ⚡ Node C — Physical Executor

**Type:** Local Python (Zero API calls)
**Purpose:** Execute real actions on local filesystem

### Action Execution Flow

```
Receives JSON from Node B
         │
    Switch on action
         │
    ┌────┴─────────────────────────────────┐
    │    TASKS          HEALTH             │
    │    LOG_TASK   →   LOG_MEDICATION     │
    │    COMPLETE   →   LOG_APPOINTMENT    │
    │    DELETE     →   LIST_HEALTH        │
    │    LIST       │                      │
    │    SEARCH     │   EVENTS             │
    │    PRIORITY   →   LOG_EVENT          │
    │               →   ADD_GUEST          │
    │    GARDEN     →   LIST_EVENTS        │
    │    LOG_PLANT  │                      │
    │    LOG_TASK   │                      │
    │    LIST       │                      │
    └───────────────┴──────────────────────┘
         │
    Writes to local JSON files
         │
    Returns confirmation string
         │
    Triggers Windows notification (if needed)
```

---

## 🛡️ Guardian Mode — Deep Dive

### Startup Sequence

```
App launches (python core_agent.py)
         │
         ├── MCP Server thread starts (port 8765)
         ├── Windows notification: "Aether is ready!"
         ├── 3 second delay
         └── Guardian thread starts (daemon=True)
                    │
                    └── First check runs immediately
                               │
                               └── Then waits 30-60 min
                                   (based on risk level)
```

### Check 1 — Missed Medications

```python
# Logic:
if morning medications exist AND current time >= 10:00 AM:
    for each morning medication:
        send Windows notification: "MISSED DOSE: {med_name}"
        add to alerts list
        add "HEALTH" to risks
```

### Check 2 — Overdue Tasks

```python
# Logic:
for each pending HIGH priority task:
    if due_date < today:
        days_overdue = today - due_date
        if days_overdue >= 2:
            send Windows notification: "CRITICAL: {task} overdue {n} days"
            add to alerts
```

### Check 3 — Upcoming Events

```python
# Logic:
for each event:
    days_until = event_date - today
    if days_until == 0:
        notify: "EVENT TODAY: {event}"
    elif days_until == 1:
        notify: "EVENT TOMORROW: {event}"
```

### Check 4 — Health Pattern + Auto Decision

```python
# Logic:
historical_misses = count "MISSED" in analytics CSV

adherence = 100 - (historical_misses / total_days * 100)

if historical_misses >= 2:
    escalate risk to HIGH
    increase monitoring to every 30 minutes
    send escalation notification

if historical_misses >= 3:
    if no doctor task exists already:
        AUTO-CREATE task: "GUARDIAN ALERT: Schedule doctor visit"
        priority: HIGH
        due: today + 2 days
        send Windows notification: "Auto-Action Taken"
```

---

## 🔌 MCP Server — Implementation Details

### Server Architecture

```
mcp_server.py runs as HTTP server on port 8765
         │
         Uses Python's built-in HTTPServer
         No external dependencies needed
         │
    ┌────┴────────────────────────────────┐
    │  MCPHandler (BaseHTTPRequestHandler) │
    │                                     │
    │  do_GET():                          │
    │    /  → server info + tool list     │
    │    /get_current_datetime → Tool 1   │
    │    /check_overdue_tasks  → Tool 2   │
    │    /get_medication_due_today→Tool 3 │
    │    /get_upcoming_events  → Tool 4   │
    │    /generate_daily_briefing→Tool 5  │
    │    unknown → 404 + available list   │
    └─────────────────────────────────────┘
```

### Tool 5 — Daily Briefing (Flagship)

```
generate_daily_briefing() calls all 4 other tools internally:
         │
         ├── get_current_datetime()
         ├── check_overdue_tasks()
         ├── get_medication_due_today()
         └── get_upcoming_events()
                    │
                    └── Combines into intelligent briefing:
                        "Good morning! Today is [date].
                         You have [N] HIGH priority tasks.
                         WARNING: [N] tasks overdue!
                         Remember medications: [list].
                         Upcoming: [event] in [N] days."
```

### Integration with Main Agent

```
User clicks "Get Daily Briefing (MCP)" button
         │
         ▼
run_daily_briefing() in core_agent.py
         │
         HTTP GET → http://127.0.0.1:8765/generate_daily_briefing
         │
         ← JSON response from MCP server
         │
         Displays in UI with summary stats
```

---

## 🔒 Four-Layer Security Architecture

```
LAYER 1: PRE-FLIGHT GUARDRAIL (Local)
─────────────────────────────────────
Input → scan for banned structures → BLOCK if found
No API call wasted. Instant rejection.

LAYER 2: PRIVACY ANALYST (AI)
──────────────────────────────
Input → detect PII → redact → pass clean intent only
Passwords, SSN, banking info never reach Gemini.

LAYER 3: DATA LOCALITY
───────────────────────
All storage → local JSON/text files only
No cloud DB, no external service, no account needed
User can read/edit/delete all data at any time.

LAYER 4: TRANSPARENT ANALYTICS
────────────────────────────────
Every action → logged to local CSV with sanitized data only
User can audit exactly what agent did and when.
```

---

## 📊 Quota Optimization

```
TRADITIONAL PIPELINE:          AETHER PIPELINE:
─────────────────────          ────────────────
API Call 1 → Privacy           Single API Call:
API Call 2 → Classify          • Privacy (Node A)
API Call 3 → Generate          • Classify (Node B)
                               • Generate message
= 3 calls per request          = 1 call per request

On free tier (20 RPD):         On free tier (20 RPD):
20 ÷ 3 = ~6 interactions/day  20 ÷ 1 = 20 interactions/day

Guardian Mode  = 0 API calls (local Python only)
Node C         = 0 API calls (local Python only)
MCP Server     = 0 API calls (reads local files only)
```

---

## 🧠 Conversation Context System

```
User: "Add task: Call doctor tomorrow"
         │ → stored in context history
         ▼
Agent: "Task added: Call doctor"

User: "Mark that as done"
         │ → reads context history
         │ → finds last task = "Call doctor"
         ▼
Agent: "Completed: Call doctor" ✅

Context keeps last 6 exchanges (12 messages)
Auto-purges oldest when limit reached
Never persisted to disk — session only
```

---

## 🗂️ Complete File Structure

```
aether-concierge-agent/
│
├── core_agent.py              # Main agent (~1400+ lines)
│   │
│   ├── INITIALIZATION
│   │   ├── load_dotenv()
│   │   ├── genai.Client setup
│   │   └── Path constants
│   │
│   ├── CONVERSATION CONTEXT
│   │   ├── conversation_history[]
│   │   ├── add_to_context()
│   │   └── get_context_summary()
│   │
│   ├── SECURITY
│   │   └── local_security_gate()
│   │
│   ├── STORAGE HELPERS
│   │   ├── load_json_file()
│   │   └── save_json_file()
│   │
│   ├── WINDOWS NOTIFICATIONS
│   │   ├── send_windows_notification()
│   │   ├── schedule_notification()
│   │   └── parse_reminder_time()
│   │
│   ├── MEMORY SYSTEM
│   │   ├── get_memory()
│   │   └── save_memory()
│   │
│   ├── TASK MANAGEMENT
│   │   ├── get_tasks()
│   │   ├── save_tasks()
│   │   ├── generate_task_id()
│   │   └── format_tasks_display()
│   │
│   ├── DOMAIN DATA
│   │   ├── get_health_data()
│   │   ├── get_events()
│   │   └── get_garden_data()
│   │
│   ├── NODE A + B (Combined)
│   │   └── smart_concierge_brain()
│   │
│   ├── NODE C
│   │   └── execute_action() [16 actions]
│   │
│   ├── GUARDIAN MODE
│   │   ├── guardian_status{}
│   │   ├── run_guardian_monitor()
│   │   ├── generate_intervention_plan()
│   │   └── get_guardian_report()
│   │
│   ├── ANALYTICS
│   │   ├── log_to_ledger()
│   │   └── get_dashboard_summary()
│   │
│   ├── PDF EXPORT
│   │   └── generate_pdf_report()
│   │
│   ├── PIPELINE
│   │   └── run_agent_pipeline()
│   │
│   └── GRADIO UI (6 tabs)
│       ├── Agent tab
│       ├── Memory tab
│       ├── My Data tab
│       ├── Analytics tab
│       ├── Guardian tab
│       └── About tab
│
├── mcp_server.py              # MCP HTTP Server (~300 lines)
│   ├── get_current_datetime()
│   ├── check_overdue_tasks()
│   ├── get_medication_due_today()
│   ├── get_upcoming_events()
│   ├── generate_daily_briefing()
│   ├── MCPHandler (HTTP handler)
│   └── run_mcp_server()
│
├── AGENTS.md                  # This file
├── README.md                  # Setup guide
├── GEMINI.md                  # Gemini integration
├── .env                       # API key (NOT committed)
├── .gitignore                 # Protects: .env, Test_Desktop/,
│                              # memory.json, analytics CSV
└── pyproject.toml             # Dependencies
```

---

## ✅ Key Concepts Demonstrated

| Concept | Where | Evidence |
|---------|-------|---------|
| Multi-agent system | Code | Node A → Node B → Node C pipeline in core_agent.py |
| MCP Server | Code | mcp_server.py HTTP server on port 8765 |
| Antigravity IDE | Video | Built entirely in Antigravity |
| Security features | Code + Video | 4-layer security, PII redaction, guardrail |
| Deployability | Video | Runs locally, launches with PS1 script |
| Agent skills | Code + Video | Guardian autonomous monitoring, auto-actions |

---

## 🚀 Setup Instructions

```bash
# 1. Clone repository
git clone https://github.com/aadiiisinggh118-byte/aether-concierge-agent.git
cd aether-concierge-agent

# 2. Install dependencies
pip install gradio google-genai python-dotenv

# 3. Set API key
# Create .env file with:
GEMINI_API_KEY=your_gemini_api_key_here
# Get free key at: https://aistudio.google.com/apikey

# 4. Run
python core_agent.py

# 5. Access
# Main UI:    http://localhost:7860
# MCP Server: http://127.0.0.1:8765
# MCP Tools:  http://127.0.0.1:8765/generate_daily_briefing
```

---

## 💬 Sample Commands

```bash
# Tasks
"Add urgent task: Submit Kaggle project by July 6"
"Mark last task as done"
"Search tasks: doctor"
"Show all my tasks"

# Health  
"Log medication: Vitamin D 1000mg every morning"
"Add appointment: Doctor checkup next Monday at 2pm"

# Events
"Plan birthday party for next Saturday with John and Sarah"
"Add guest: Mike to the birthday party"

# Garden
"Add tomato plant to garden"

# MCP Integration
"Get Daily Briefing (MCP)"  # Queries MCP server

# Guardian (Automatic — no input needed)
# Starts monitoring immediately when app launches
# Checks autonomously every 30-60 minutes
# Sends Windows alerts when risks detected
# Auto-creates tasks when health adherence drops
```

---

*🛡️ Aether Concierge — Protecting your life autonomously*
*Privacy-First · Local-First · Always Watching · Never Sharing*