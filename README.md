# 🛡️ Aether Concierge

> **Privacy-First Autonomous Life Guardian**
> Built for the Google x Kaggle 5-Day AI Agents Intensive — Capstone 2026
> Track: **Concierge Agents**

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?style=flat-square)
![Gradio](https://img.shields.io/badge/Gradio-6.x-green?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-HTTP%20Server-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)

---

## 🌟 What is Aether Concierge?

Aether Concierge is a **privacy-first autonomous life guardian** that helps individuals and families manage their daily lives across four critical domains — while keeping ALL personal data stored locally on your own machine.

The agent doesn't just respond to commands. It **monitors your life autonomously**, detects risks before they become problems, and takes corrective action — all without you asking.

> *"Your data never leaves your machine. Aether watches over your life so you don't have to."*

---

## ✨ Key Features

### 🤖 Multi-Agent Pipeline
- **Node A** — Privacy Analyst: Sanitizes and redacts PII before any AI processing
- **Node B** — Logic Engine: Classifies intent into 16 action types across 4 domains
- **Node C** — Physical Executor: 100% local execution, zero additional API calls

### 🛡️ Guardian Mode (Autonomous)
- Runs in background every 30-60 minutes without user input
- Detects missed medications, overdue tasks, upcoming events
- **Auto Decision Engine**: Creates doctor tasks automatically when health adherence drops
- Generates dynamic intervention plans with specific recommendations
- Sends real Windows desktop notifications proactively
- Adapts monitoring frequency based on risk level (LOW/MEDIUM/HIGH/CRITICAL)

### 🔌 Real MCP Server
- Separate HTTP server running on port 8765
- 5 tools accessible by any external agent via HTTP
- Try: `http://127.0.0.1:8765/generate_daily_briefing`

### 🔒 Privacy-First Architecture
- All personal data stored locally in JSON/text files
- Automatic PII redaction before AI processing
- Security gate blocks dangerous system commands
- Transparent analytics CSV for full auditability
- No cloud storage, no accounts, no subscriptions

### 📊 Analytics Dashboard
- Real-time charts from actual usage data
- Domain usage breakdown
- Daily activity tracking
- Top actions visualization

### 📄 PDF Export
- One-click full report generation
- Tasks, health, events, garden summary
- Opens in browser for easy printing

---

## 🏗️ Architecture Overview

```
User Input
    │
    ▼
[Security Gate] ──── Dangerous? ──── BLOCK
    │
    ▼
[Node A: Privacy Analyst] ◄── Single Gemini 2.5 Flash API Call
    │   Redacts PII, classifies domain, selects action
    ▼
[Node B: Logic Engine] (same API call)
    │   Returns structured JSON
    ▼
[Node C: Physical Executor] ◄── 100% Local, Zero API calls
    │   Executes on local files
    ▼
[Analytics Ledger] ──── Local CSV only

════════ Running in parallel ════════

[Guardian Mode] ──── Background thread, autonomous
    │   Monitors every 30-60 min
    ▼
[Auto Decision Engine]
    │   Auto-creates tasks, escalates risk
    ▼
[Intervention Plan] ──── Dynamic recommendations

[MCP Server] ──── HTTP on port 8765
    │   5 tools for external agents
    ▼
[Daily Briefing] ──── Intelligent morning summary
```

---

## 🌍 Life Domains

| Domain | What it handles | Actions |
|--------|----------------|---------|
| ✅ **Tasks** | To-dos, reminders, priorities | Log, Complete, Delete, Search, List, Update Priority |
| 💊 **Health** | Medications, appointments | Log Medication, Log Appointment, List Health |
| 🎉 **Events** | Parties, gatherings, guests | Log Event, Add Guest, List Events |
| 🌱 **Garden** | Plants, home tasks | Log Plant, Log Garden Task, List Garden |

---

## 🔌 MCP Server Tools

| Endpoint | Description |
|----------|-------------|
| `GET /` | Server info and available tools |
| `GET /get_current_datetime` | Current date, time, day of week |
| `GET /check_overdue_tasks` | All tasks past their due date |
| `GET /get_medication_due_today` | Medications scheduled for today |
| `GET /get_upcoming_events?days=7` | Events in next N days |
| `GET /generate_daily_briefing` | Complete intelligent morning briefing |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```bash
# 1. Clone
git clone https://github.com/aadiiisinggh118-byte/aether-concierge-agent.git
cd aether-concierge-agent

# 2. Install dependencies
pip install gradio google-genai python-dotenv

# 3. Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env

# 4. Run
python core_agent.py

# 5. Open browser
# Main UI:    http://localhost:7860
# MCP Server: http://127.0.0.1:8765
```

---

## 💬 Example Commands

```
# Tasks
"Add urgent task: Submit Kaggle project by July 6"
"Mark last task as done"
"Search tasks: doctor"
"Show all my tasks"
"Change its priority to high"  ← uses conversation context

# Health
"Log medication: Vitamin D 1000mg every morning"
"Add appointment: Doctor checkup next Monday at 2pm"
"List health summary"

# Events
"Plan birthday party for next Saturday with John and Sarah"
"Add guest: Mike to the birthday party"
"Show upcoming events"

# Garden
"Add tomato plant to garden"
"Log garden task: Water plants every Sunday"

# MCP
"Get Daily Briefing (MCP)"  ← queries MCP server via HTTP

# Guardian (automatic - no commands needed!)
# Starts monitoring when app launches
# Sends Windows notifications autonomously
# Creates tasks automatically when needed
```

---

## 🖥️ UI Overview

The app has **6 tabs:**

| Tab | Purpose |
|-----|---------|
| 🚀 **Agent** | Main command interface with dashboard |
| 🧠 **Memory** | Set permanent rules Aether always follows |
| 📁 **My Data** | View all stored data across all domains |
| 📊 **Analytics** | Real usage charts from your data |
| 🛡️ **Guardian** | Autonomous monitoring status and reports |
| ℹ️ **About** | Architecture and feature documentation |

---

## 🛡️ Guardian Mode — How It Works

Guardian Mode is what makes Aether a true autonomous agent:

```
Every 30-60 minutes (automatic):

1. CHECK missed medications (after 10am)
   → Windows notification if missed
   → Health risk flag raised

2. CHECK overdue high-priority tasks (2+ days)
   → CRITICAL notification sent
   → Task escalation triggered

3. CHECK events in next 24 hours
   → Reminder notification sent

4. ANALYZE health patterns (from history)
   → Calculate medication adherence %
   → If adherence drops: escalate risk
   → If 3+ misses: AUTO-CREATE doctor task

5. GENERATE intervention plan
   → Problems detected
   → Actions taken by Guardian
   → Dynamic recommendations
   → Next check time
```

---

## 🔒 Privacy Architecture

```
LAYER 1 — Security Gate (Local)
   Blocks dangerous commands before any processing
   No API quota wasted on malicious input

LAYER 2 — Privacy Analyst (AI)
   Redacts: passwords, SSNs, banking info, API keys
   Gemini never sees raw personal data

LAYER 3 — Data Locality
   All data: local JSON/text files only
   No cloud, no accounts, no subscriptions

LAYER 4 — Transparent Analytics
   Every action logged locally
   User can audit everything at any time
```

---

## 📁 Project Structure

```
aether-concierge-agent/
├── core_agent.py              # Main agent (~1400+ lines)
├── mcp_server.py              # Real MCP HTTP server (~300 lines)
├── AGENTS.md                  # Complete agent architecture docs
├── README.md                  # This file
├── GEMINI.md                  # Gemini integration guide
├── .env                       # API key (NOT committed)
├── .gitignore                 # Protects sensitive files
├── pyproject.toml             # Project dependencies
└── Test_Desktop/              # Local data sandbox (auto-created)
    ├── daily_tasks.json       # Your tasks
    ├── health_tracker.json    # Medications & appointments
    ├── events.json            # Events & guest lists
    └── garden_planner.json    # Plants & garden tasks
```

---

## 📖 Documentation

- **[AGENTS.md](./AGENTS.md)** — Complete agent architecture with diagrams
- **[GEMINI.md](./GEMINI.md)** — Gemini model integration guide

---

## 🔑 Key Concepts Demonstrated

| Concept | Where |
|---------|-------|
| Multi-agent system (ADK) | `core_agent.py` — Node A/B/C pipeline |
| MCP Server | `mcp_server.py` — HTTP server port 8765 |
| Antigravity IDE | Video — built entirely in Antigravity |
| Security features | `core_agent.py` — 4-layer security |
| Deployability | Video — local deployment with launcher |
| Agent skills | `core_agent.py` — Guardian autonomous mode |

---

## 🏆 Built For

**Google x Kaggle 5-Day AI Agents Intensive — Capstone 2026**
Track: Concierge Agents

> *"The opportunity for personal AI agents to streamline and simplify people's lives is incredible. Safe and secure agents can free time for things that really matter."*

---

*🛡️ Aether Concierge — Your data. Your device. Your guardian.*