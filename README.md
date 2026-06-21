# 🛡️ Aether Concierge — Privacy-First Personal Life Agent

> **Your personal AI concierge that keeps your data on YOUR machine.**  
> Built for the Google x Kaggle 5-Day AI Agents Intensive — Capstone 2026  
> Track: **Concierge Agents**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?style=flat-square)
![Gradio](https://img.shields.io/badge/Gradio-6.x-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## 🌟 What is Aether Concierge?

Aether Concierge is a **privacy-first multi-agent AI system** that helps individuals and families manage their daily lives across four critical life domains — all while keeping every piece of personal data stored **locally on your own machine**.

The AI never sees your raw personal data. It only processes sanitized, redacted intent. Your medication names, guest lists, and daily tasks never leave your device.

---

## ✨ Features

### 4 Life Domains in One Agent

| Domain | What it handles |
|--------|----------------|
| ✅ **Tasks** | Daily to-dos, reminders, personal notes |
| 💊 **Health** | Medications, doctor appointments, health tracking |
| 🎉 **Events** | Party planning, guest lists, family gatherings |
| 🌱 **Garden** | Plant tracking, garden tasks, home planning |

### Privacy-First Architecture
- 🔒 All data stored locally as JSON/text files — never in the cloud
- 🛡️ Automatic redaction of passwords, SSNs, banking info before any AI processing
- ⛔ Security gate blocks dangerous system commands
- 📊 Local analytics ledger for full transparency

### Quota-Optimized Design
- **1 API call per request** (vs 3 in traditional pipelines)
- Uses Gemini 2.5 Flash — most capable free-tier model
- Node C (Physical Executor) is 100% local Python — zero API calls

---

## 🏗️ Architecture

```
User Input
    │
    ▼
[PRE-FLIGHT GUARDRAIL] ── Dangerous command? ──► BLOCK
    │
    ▼
[NODE A: PRIVACY ANALYST] ◄─── Single Gemini 2.5 Flash API Call
    │   Redacts sensitive data
    │   Classifies domain + action
    │   Extracts structured data
    ▼
[NODE B: LOGIC ENGINE] (same API call — saves quota)
    │   12 action types across 4 domains
    │   Returns strict JSON
    ▼
[NODE C: PHYSICAL EXECUTOR] ◄── 100% Local, Zero API calls
    │   Executes on local files
    │   Returns confirmation
    ▼
[ANALYTICS LEDGER] ── Local CSV only
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/aadiiisinggh118-byte/aether-concierge-agent.git
cd aether-concierge-agent
```

### 2. Install dependencies
```bash
pip install gradio google-genai python-dotenv
```

### 3. Set up your API key
Create a `.env` file in the root directory:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
Get your free API key at: https://aistudio.google.com/apikey

### 4. Run the agent
```bash
python core_agent.py
```

### 5. Open in browser
```
http://localhost:7860
```

---

## 💬 Example Commands

```
"Add task: Call doctor tomorrow at 3pm"
"Log medication: Vitamin D 1000mg every morning"
"Plan birthday party for next Saturday with John and Sarah"
"Add tomato plant to garden"
"Show all my tasks"
"List health summary"
"Show upcoming events"
"Add guest: Mike to the birthday party"
```

---

## 📁 Project Structure

```
aether-concierge-agent/
├── core_agent.py              # Main agent — all nodes + UI
├── AGENTS.md                  # Agent architecture documentation
├── GEMINI.md                  # Gemini model guide
├── .env                       # API key (NOT committed — protected)
├── .gitignore                 # Protects sensitive files
├── pyproject.toml             # Project dependencies
├── memory.json                # Persistent memory (auto-created)
├── concierge_analytics.csv    # Analytics ledger (auto-created)
├── Test_Desktop/              # Local data sandbox (auto-created)
│   ├── daily_tasks.txt        # Your tasks
│   ├── health_tracker.json    # Medications & appointments
│   ├── events.json            # Events & guest lists
│   └── garden_planner.json    # Plants & garden tasks
├── app/                       # Additional app modules
├── deployment/                # Deployment configs
└── tests/                     # Test suite
```

---

## 🛡️ Privacy & Security

Aether Concierge was built with privacy as the **first principle**, not an afterthought:

- **No cloud storage** — All your data lives in local JSON and text files you can read, edit, or delete anytime
- **Redaction before AI** — The Privacy Analyst node strips sensitive data before sending anything to the Gemini API
- **Transparent logging** — Every agent action is logged to a local CSV file you can inspect
- **Security gate** — Banned command structures are blocked before any processing begins
- **Open source** — You can read every line of code and verify exactly what happens to your data

---

## 🧠 Long-Term Memory

Aether remembers your preferences across sessions:

1. Go to the **Memory tab** in the UI
2. Type a rule like: *"Always prioritize health tasks"*
3. Click **Save Rule**
4. From now on, every agent call uses this rule

Memory is stored locally in `memory.json`.

---

## 📊 Analytics

Every agent interaction is logged to `concierge_analytics.csv`:

| Timestamp | Domain | Action | Safe_Input | Result |
|-----------|--------|--------|------------|--------|
| 2026-06-21 10:30 | TASKS | LOG_TASK | Add task: Call doctor | ✅ Task logged |
| 2026-06-21 10:31 | HEALTH | LOG_MEDICATION | Log Vitamin D | 💊 Medication logged |

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Google Gemini 2.5 Flash |
| UI Framework | Gradio 6.x |
| Data Storage | Local JSON + TXT |
| Python SDK | google-genai |
| Environment | python-dotenv |

---

## 📖 Documentation

- **[AGENTS.md](./AGENTS.md)** — Full agent architecture documentation
- **[GEMINI.md](./GEMINI.md)** — Gemini model integration guide

---

## 🏆 Built For

Google x Kaggle **5-Day AI Agents Intensive** — Capstone Project 2026  
Track: **Concierge Agents** — *Safe and secure agents for individual, family and social challenges*

---

*Your data. Your device. Your concierge.* 🛡️