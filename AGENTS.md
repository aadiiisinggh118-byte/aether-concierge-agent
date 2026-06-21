# 🛡️ Aether Concierge — Agent Architecture Documentation

> **Privacy-First Personal Life Management Agent**  
> Built for the Google x Kaggle 5-Day AI Agents Intensive — Capstone 2026  
> Track: **Concierge Agents**

---

## 🧭 Overview

Aether Concierge is a **privacy-first multi-agent system** that helps individuals and families manage their daily lives across four critical life domains — Tasks, Health, Events, and Garden — while keeping all personal data secure and local.

The core philosophy: **Your data never leaves your machine.** The AI only ever sees sanitized, redacted intent — never your raw personal information.

---

## 🏗️ Agent Architecture

### System Flow

```
User Input
    │
    ▼
[PRE-FLIGHT GUARDRAIL] ──── Banned structure detected? ──► BLOCK & ALERT
    │
    ▼ (safe input)
[NODE A: PRIVACY ANALYST] ◄── Gemini 2.5 Flash (Single API Call)
    │   • Redacts passwords, SSNs, banking info
    │   • Extracts clean operational intent
    │   • Classifies domain + action
    │   • Extracts structured data
    ▼
[NODE B: LOGIC ENGINE]  (runs inside same API call — no extra quota)
    │   • Domain: TASKS | HEALTH | EVENTS | GARDEN
    │   • Action: 12 specific action types
    │   • Structured JSON output
    ▼
[NODE C: PHYSICAL EXECUTOR] ◄── 100% Local, Zero API calls
    │   • Executes action on local files
    │   • Reads/writes JSON & text files
    │   • Returns confirmation
    ▼
[ANALYTICS LEDGER] ──────── Local CSV logging only
    │
    ▼
User sees result
```

---

## 🤖 Agent Nodes

### Node A — Privacy Analyst
**Role:** Sanitizes and understands user intent  
**Model:** Gemini 2.5 Flash  
**Responsibility:**
- Scans raw user input for sensitive data (passwords, SSNs, banking info, private keys)
- Replaces sensitive data with `[REDACTED]` placeholders
- Outputs clean, safe operational intent
- Works in conjunction with Node B in a single API call to save quota

**Example:**
```
Input:  "Add task: Pay $5000 from account #4521-XXXX to landlord"
Output: "Add task: Pay [REDACTED] from account [REDACTED] to landlord"
```

---

### Node B — Logic Engine (Strict Classification)
**Role:** Classifies intent into structured action plan  
**Model:** Gemini 2.5 Flash (same call as Node A)  
**Responsibility:**
- Classifies intent into one of 4 domains
- Maps to one of 12 specific action types
- Extracts structured data (title, date, time, people, notes, quantity)
- Returns strict JSON — no free-form text

**Supported Actions:**

| Domain | Actions |
|--------|---------|
| TASKS  | `LOG_TASK`, `COMPLETE_TASK`, `LIST_TASKS` |
| HEALTH | `LOG_MEDICATION`, `LOG_APPOINTMENT`, `LIST_HEALTH` |
| EVENTS | `LOG_EVENT`, `ADD_GUEST`, `LIST_EVENTS` |
| GARDEN | `LOG_PLANT`, `LOG_GARDEN_TASK`, `LIST_GARDEN` |
| — | `UNKNOWN` |

---

### Node C — Physical Executor
**Role:** Executes real-world actions locally  
**Model:** None — pure Python, zero API calls  
**Responsibility:**
- Reads action plan from Node B
- Executes against local files in the sandbox
- All data stored as JSON or plain text on user's machine
- Returns human-readable confirmation

**Local Storage Files:**
```
Test_Desktop/
├── daily_tasks.txt        # Task list (plain text)
├── health_tracker.json    # Medications & appointments
├── events.json            # Events & guest lists
└── garden_planner.json    # Plants & garden tasks
```

---

## 🛡️ Security Architecture

### Pre-Flight Guardrail
Local rule-based check **before any API call**:
```python
banned_structures = [
    "sudo rm", "format c:", "--bypass_rules", "delete_all",
    "rm -rf", "os.system", "subprocess", "eval(", "exec("
]
```
Raises `PermissionError` immediately — no API quota wasted on malicious input.

### Privacy Sanitization (Node A)
Automatic redaction categories:
- Passwords and secret keys
- Banking account numbers and card numbers  
- Social Security Numbers (SSN)
- Private API keys

### Data Locality
- ✅ All user data stored on local machine only
- ✅ Gemini API only receives sanitized intent (not raw personal data)
- ✅ No cloud database, no external storage
- ✅ Analytics CSV stored locally for user inspection

---

## ⚡ Quota Optimization Strategy

### The Problem
Traditional 3-node pipelines make **3 separate API calls** per user request:
- Call 1: Privacy Analyst
- Call 2: Logic Engine  
- Call 3: Response Generator

On free tier (20 RPD), this means only **6-7 usable requests per day**.

### Our Solution: Single Smart Call
Aether combines Nodes A + B into **one structured JSON prompt** that:
1. Sanitizes the input
2. Classifies the domain and action
3. Extracts structured data
4. Generates a user message

**Result: 1 API call per user request** = 3x more efficient = ~20 usable requests per day.

Node C (Physical Executor) is 100% local Python — **zero API calls**.

---

## 🧠 Long-Term Memory System

Aether supports persistent user preferences stored in `memory.json`:

```json
{
  "rules": [
    "Always prioritize health tasks over garden tasks",
    "Sunday is garden maintenance day"
  ],
  "preferences": {}
}
```

Rules are injected into every prompt, allowing the agent to personalize behavior across sessions without retraining.

---

## 📊 Analytics & Observability

Every agent run is logged to `concierge_analytics.csv`:

| Timestamp | Domain | Action | Safe_Input | Result |
|-----------|--------|--------|------------|--------|
| 2026-06-21 10:30:22 | TASKS | LOG_TASK | Add task: Call doctor | ✅ Task logged |
| 2026-06-21 10:31:45 | HEALTH | LOG_MEDICATION | Log Vitamin D 1000mg | 💊 Medication logged |

This enables:
- Usage pattern analysis
- Agent behavior auditing
- Privacy compliance verification (confirming only sanitized data is logged)

---

## 🌟 Real-World Impact

### Problems Solved

**For individuals:**
- Consolidates task management, health tracking, event planning, and home management into one private agent
- No subscription fees, no cloud accounts, no data harvesting

**For families:**
- Elderly care: medication tracking with dose and timing
- Family events: guest list management, party planning
- Home management: garden planning, household task coordination

**For privacy-conscious users:**
- Full transparency: all stored data viewable in plain JSON/text files
- No black-box cloud storage
- User controls exactly what the agent remembers

---

## 🔧 Technical Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Google Gemini 2.5 Flash |
| UI Framework | Gradio 5.x |
| Data Storage | Local JSON + TXT files |
| Python SDK | google-genai |
| Environment | python-dotenv |
| Analytics | CSV (stdlib) |
| Security | Custom rule-based guardrail |

---

## 🚀 Running the Agent

```bash
# 1. Install dependencies
pip install google-genai gradio python-dotenv

# 2. Set your API key
echo "GEMINI_API_KEY=your_key_here" > .env

# 3. Run
python core_agent.py

# 4. Open browser
# http://localhost:7860
```

---

## 📁 Project Structure

```
aether-concierge-agent/
├── core_agent.py              # Main agent (all nodes)
├── AGENTS.md                  # This file
├── GEMINI.md                  # Gemini model documentation
├── .env                       # API key (not committed)
├── .gitignore
├── pyproject.toml
├── memory.json                # Persistent memory (auto-created)
├── concierge_analytics.csv    # Analytics ledger (auto-created)
├── Test_Desktop/              # Sandbox (auto-created)
│   ├── daily_tasks.txt
│   ├── health_tracker.json
│   ├── events.json
│   └── garden_planner.json
├── app/                       # Additional app modules
├── deployment/                # Deployment configs
└── tests/                     # Test suite
```

---

## 🔮 Future Roadmap

- [ ] Voice input support (Gemini Live API)
- [ ] Calendar integration (Google Calendar API)
- [ ] Multi-user family profiles with role-based access
- [ ] Agent-to-Agent (A2A) protocol for specialist sub-agents
- [ ] Email digest generation (weekly summary)
- [ ] Medication reminder notifications

---

*Built with privacy, care, and the lessons from 5 days of Google x Kaggle AI Agents Intensive.