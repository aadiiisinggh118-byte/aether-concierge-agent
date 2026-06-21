import os
import csv
import json
import shutil
import gradio as gr
from datetime import datetime, date
from google import genai
from dotenv import load_dotenv

# ==========================================
# PHASE 1: SECURE INITIALIZATION
# ==========================================
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("SECURITY ALERT: API Key not found in .env file.")

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"  # Upgraded model - more capable, quota-safe

SANDBOX_PATH = os.path.join(os.getcwd(), "Test_Desktop")
MEMORY_FILE = "memory.json"
TASKS_FILE = os.path.join(SANDBOX_PATH, "daily_tasks.txt")
HEALTH_FILE = os.path.join(SANDBOX_PATH, "health_tracker.json")
EVENTS_FILE = os.path.join(SANDBOX_PATH, "events.json")
GARDEN_FILE = os.path.join(SANDBOX_PATH, "garden_planner.json")
ANALYTICS_FILE = "concierge_analytics.csv"

# ==========================================
# PRE-FLIGHT GUARDRAIL
# ==========================================
def local_security_gate(user_input: str):
    banned_structures = [
        "sudo rm", "format c:", "--bypass_rules", "delete_all",
        "rm -rf", "os.system", "subprocess", "eval(", "exec("
    ]
    for phrase in banned_structures:
        if phrase in user_input.lower():
            raise PermissionError(f"CRITICAL: Unauthorized structure '{phrase}' detected.")

# ==========================================
# PERSISTENT STORAGE HELPERS
# ==========================================
def ensure_sandbox():
    os.makedirs(SANDBOX_PATH, exist_ok=True)

def load_json_file(filepath: str, default):
    if not os.path.exists(filepath):
        return default
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(filepath: str, data):
    ensure_sandbox()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ==========================================
# LONG-TERM MEMORY
# ==========================================
def get_memory() -> dict:
    return load_json_file(MEMORY_FILE, {"rules": [], "preferences": {}})

def save_memory(new_rule: str) -> str:
    memory = get_memory()
    if new_rule.strip() and new_rule not in memory["rules"]:
        memory["rules"].append(new_rule.strip())
    save_json_file(MEMORY_FILE, memory)
    return f"✅ Rule saved: '{new_rule}'"

def get_memory_display() -> str:
    memory = get_memory()
    rules = memory.get("rules", [])
    if not rules:
        return "No custom rules set."
    return "\n".join(f"• {r}" for r in rules)

# ==========================================
# DOMAIN DATA LOADERS
# ==========================================
def get_tasks() -> list:
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    return lines

def get_health_data() -> dict:
    return load_json_file(HEALTH_FILE, {"medications": [], "appointments": [], "notes": []})

def get_events() -> dict:
    return load_json_file(EVENTS_FILE, {"events": []})

def get_garden_data() -> dict:
    return load_json_file(GARDEN_FILE, {"plants": [], "tasks": [], "notes": []})

# ==========================================
# CORE: SINGLE SMART API CALL (Quota Saver)
# ==========================================
def smart_concierge_brain(user_input: str) -> dict:
    """
    ONE single Gemini API call that handles everything:
    - Privacy sanitization
    - Intent classification  
    - Action planning
    - Response generation
    This replaces the old 3-call architecture, saving 3x quota.
    """
    memory = get_memory()
    rules_text = "\n".join(memory.get("rules", [])) or "None"
    today = date.today().strftime("%A, %B %d, %Y")

    system_prompt = f"""You are Aether Concierge - an advanced privacy-first personal AI agent.
Today's date: {today}
User's custom memory rules:
{rules_text}

You handle FOUR life domains for the user:
1. TASKS - daily to-dos, reminders, personal notes
2. HEALTH - medications, doctor appointments, health notes
3. EVENTS - parties, gatherings, family events, invitations
4. GARDEN - plants, garden tasks, home planner

PRIVACY RULE: Redact passwords, banking info, SSN with [REDACTED]. Keep personal names.

STEP 1 - SANITIZE: Remove any sensitive private data from the user's request.
STEP 2 - CLASSIFY: Pick the best action from this list:
  - LOG_TASK: Add a task/reminder/to-do
  - COMPLETE_TASK: Mark a task as done
  - LIST_TASKS: Show all current tasks
  - LOG_MEDICATION: Add/track a medication
  - LOG_APPOINTMENT: Add a doctor/health appointment
  - LIST_HEALTH: Show health summary
  - LOG_EVENT: Create/plan an event
  - ADD_GUEST: Add guests to an event
  - LIST_EVENTS: Show upcoming events
  - LOG_PLANT: Add a plant to garden
  - LOG_GARDEN_TASK: Add garden task
  - LIST_GARDEN: Show garden summary
  - UNKNOWN: Cannot determine action

STEP 3 - EXTRACT: Pull out the key data needed to execute the action.

Respond ONLY in this exact JSON format, no other text:
{{
  "safe_input": "sanitized version of user input",
  "domain": "TASKS|HEALTH|EVENTS|GARDEN|UNKNOWN",
  "action": "ACTION_NAME",
  "extracted_data": {{
    "title": "main item title or description",
    "date": "date if mentioned or null",
    "time": "time if mentioned or null",
    "people": ["list of people mentioned"],
    "notes": "any extra details",
    "quantity": "amount/dose if health related or null"
  }},
  "user_message": "friendly confirmation message to show the user (1-2 sentences)"
}}

USER INPUT: {user_input}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=system_prompt
    )
    
    raw = response.text.strip()
    # Clean markdown fences if present
    raw = raw.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "safe_input": user_input,
            "domain": "UNKNOWN",
            "action": "UNKNOWN",
            "extracted_data": {"title": user_input, "date": None, "time": None,
                               "people": [], "notes": "", "quantity": None},
            "user_message": "I understood your request but couldn't classify it. Please try rephrasing."
        }

# ==========================================
# NODE C: PHYSICAL EXECUTOR (All Domains)
# ==========================================
def execute_action(brain_result: dict) -> str:
    ensure_sandbox()
    action = brain_result.get("action", "UNKNOWN")
    data = brain_result.get("extracted_data", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = data.get("title", "Untitled")
    date_val = data.get("date", "")
    time_val = data.get("time", "")
    people = data.get("people", [])
    notes = data.get("notes", "")
    quantity = data.get("quantity", "")

    # --- TASKS DOMAIN ---
    if action == "LOG_TASK":
        entry = f"[{timestamp}]"
        if date_val:
            entry += f" [{date_val}]"
        if time_val:
            entry += f" [{time_val}]"
        entry += f" {title}"
        if notes:
            entry += f" | Note: {notes}"
        with open(TASKS_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
        return f"✅ Task logged: '{title}'"

    elif action == "COMPLETE_TASK":
        tasks = get_tasks()
        matched = [t for t in tasks if title.lower() in t.lower()]
        if matched:
            remaining = [t for t in tasks if title.lower() not in t.lower()]
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(remaining) + "\n")
            return f"✅ Completed & removed: '{matched[0]}'"
        return f"⚠️ No task found matching '{title}'"

    elif action == "LIST_TASKS":
        tasks = get_tasks()
        if not tasks:
            return "📋 No tasks yet! Add some tasks to get started."
        return "📋 **Your Tasks:**\n" + "\n".join(f"• {t}" for t in tasks[-10:])

    # --- HEALTH DOMAIN ---
    elif action == "LOG_MEDICATION":
        health = get_health_data()
        med = {
            "name": title,
            "dose": quantity or "Not specified",
            "time": time_val or "Not specified",
            "added": timestamp,
            "notes": notes
        }
        health["medications"].append(med)
        save_json_file(HEALTH_FILE, health)
        return f"💊 Medication logged: '{title}' | Dose: {quantity or 'Not specified'}"

    elif action == "LOG_APPOINTMENT":
        health = get_health_data()
        appt = {
            "title": title,
            "date": date_val or "Date not specified",
            "time": time_val or "Time not specified",
            "notes": notes,
            "added": timestamp
        }
        health["appointments"].append(appt)
        save_json_file(HEALTH_FILE, health)
        return f"🏥 Appointment saved: '{title}' on {date_val or 'date TBD'}"

    elif action == "LIST_HEALTH":
        health = get_health_data()
        result = []
        meds = health.get("medications", [])
        appts = health.get("appointments", [])
        if meds:
            result.append("💊 **Medications:**")
            for m in meds[-5:]:
                result.append(f"  • {m['name']} — {m['dose']} at {m['time']}")
        if appts:
            result.append("🏥 **Appointments:**")
            for a in appts[-5:]:
                result.append(f"  • {a['title']} on {a['date']} at {a['time']}")
        if not result:
            return "🏥 No health records yet. Start by logging a medication or appointment."
        return "\n".join(result)

    # --- EVENTS DOMAIN ---
    elif action == "LOG_EVENT":
        events_data = get_events()
        event = {
            "id": len(events_data["events"]) + 1,
            "title": title,
            "date": date_val or "Date TBD",
            "time": time_val or "Time TBD",
            "guests": people,
            "notes": notes,
            "created": timestamp
        }
        events_data["events"].append(event)
        save_json_file(EVENTS_FILE, events_data)
        return f"🎉 Event created: '{title}' on {date_val or 'date TBD'} | Guests: {len(people)}"

    elif action == "ADD_GUEST":
        events_data = get_events()
        evs = events_data.get("events", [])
        if not evs:
            return "⚠️ No events found. Create an event first!"
        # Add to most recent event
        evs[-1]["guests"].extend(people)
        save_json_file(EVENTS_FILE, events_data)
        added = ", ".join(people) if people else "guests"
        return f"👥 Added {added} to event '{evs[-1]['title']}'"

    elif action == "LIST_EVENTS":
        events_data = get_events()
        evs = events_data.get("events", [])
        if not evs:
            return "🎉 No events planned yet. Start planning!"
        result = ["🎉 **Upcoming Events:**"]
        for e in evs[-5:]:
            guest_count = len(e.get("guests", []))
            result.append(f"  • {e['title']} — {e['date']} at {e['time']} | 👥 {guest_count} guests")
        return "\n".join(result)

    # --- GARDEN DOMAIN ---
    elif action == "LOG_PLANT":
        garden = get_garden_data()
        plant = {
            "name": title,
            "planted": date_val or timestamp[:10],
            "notes": notes,
            "added": timestamp
        }
        garden["plants"].append(plant)
        save_json_file(GARDEN_FILE, garden)
        return f"🌱 Plant added: '{title}' | Planted: {date_val or 'today'}"

    elif action == "LOG_GARDEN_TASK":
        garden = get_garden_data()
        task = {
            "task": title,
            "due": date_val or "No due date",
            "notes": notes,
            "added": timestamp
        }
        garden["tasks"].append(task)
        save_json_file(GARDEN_FILE, garden)
        return f"🌿 Garden task added: '{title}'"

    elif action == "LIST_GARDEN":
        garden = get_garden_data()
        plants = garden.get("plants", [])
        tasks = garden.get("tasks", [])
        result = []
        if plants:
            result.append(f"🌱 **Plants ({len(plants)}):**")
            for p in plants[-5:]:
                result.append(f"  • {p['name']} — planted {p['planted']}")
        if tasks:
            result.append("🌿 **Garden Tasks:**")
            for t in tasks[-5:]:
                result.append(f"  • {t['task']} — due {t['due']}")
        if not result:
            return "🌱 Garden is empty! Start by adding your plants."
        return "\n".join(result)

    else:
        return "🤔 I understood your request but wasn't sure what action to take. Try being more specific!"

# ==========================================
# ANALYTICS LEDGER
# ==========================================
def log_to_ledger(raw_input, brain_result, physical_result):
    file_exists = os.path.isfile(ANALYTICS_FILE)
    with open(ANALYTICS_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Domain", "Action", "Safe_Input", "Result"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            brain_result.get("domain", "UNKNOWN"),
            brain_result.get("action", "UNKNOWN"),
            brain_result.get("safe_input", raw_input)[:100],
            physical_result[:100]
        ])

# ==========================================
# DASHBOARD DATA
# ==========================================
def get_dashboard_summary() -> str:
    tasks = get_tasks()
    health = get_health_data()
    events = get_events()
    garden = get_garden_data()
    
    task_count = len(tasks)
    med_count = len(health.get("medications", []))
    appt_count = len(health.get("appointments", []))
    event_count = len(events.get("events", []))
    plant_count = len(garden.get("plants", []))
    
    return f"""📊 **Your Aether Dashboard**
━━━━━━━━━━━━━━━━━━━━━━
✅ Tasks: {task_count} active
💊 Medications: {med_count} tracked
🏥 Appointments: {appt_count} scheduled
🎉 Events: {event_count} planned
🌱 Plants: {plant_count} in garden
━━━━━━━━━━━━━━━━━━━━━━
Try: "Add task: call mom tomorrow"
Or: "Log medication: Vitamin D, 1000mg"
Or: "Plan birthday party for next Saturday"
Or: "Add tomato plant to garden" """

# ==========================================
# MAIN AGENT PIPELINE
# ==========================================
def run_agent_pipeline(user_command: str):
    """Main pipeline - ONE API call, local execution."""
    if not user_command or not user_command.strip():
        return "⚠️ Please enter a command.", "—", "—", "Please type something!"

    try:
        # Security gate (local, no API)
        try:
            local_security_gate(user_command)
        except PermissionError as e:
            return f"🚫 {str(e)}", "BLOCKED", "BLOCKED", str(e)

        # ONE smart API call
        brain_result = smart_concierge_brain(user_command)

        # Local execution (no API)
        physical_result = execute_action(brain_result)

        # Log to ledger (local)
        log_to_ledger(user_command, brain_result, physical_result)

        safe_input = brain_result.get("safe_input", user_command)
        action = brain_result.get("action", "UNKNOWN")
        domain = brain_result.get("domain", "UNKNOWN")
        user_msg = brain_result.get("user_message", physical_result)

        return safe_input, f"{domain} → {action}", physical_result, user_msg

    except Exception as e:
        err = str(e)
        return f"Error: {err}", "ERROR", "ABORTED", f"⚠️ System error: {err}"

# ==========================================
# GRADIO UI - POLISHED CONCIERGE INTERFACE
# ==========================================
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

body, .gradio-container {
    background: #0a0e1a !important;
    color: #e2e8f0 !important;
}

.gradio-container {
    max-width: 1100px !important;
    margin: 0 auto !important;
}

/* Header */
.aether-header {
    background: linear-gradient(135deg, #1a1f35 0%, #0d1226 100%);
    border: 1px solid #2d3561;
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.aether-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4);
}

/* Domain pills */
.domain-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin: 3px;
}

/* Cards */
.card {
    background: #111827 !important;
    border: 1px solid #1e2a45 !important;
    border-radius: 12px !important;
}

/* Input styling */
.gr-textbox textarea, .gr-textbox input {
    background: #111827 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 15px !important;
    padding: 14px !important;
}
.gr-textbox textarea:focus, .gr-textbox input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

/* Primary button */
.primary-btn button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 14px 28px !important;
    width: 100% !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}
.primary-btn button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
}

/* Secondary button */
.secondary-btn button {
    background: #1e2a45 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 13px !important;
}

/* Output boxes */
.output-box textarea {
    background: #0d1226 !important;
    border: 1px solid #1e2a45 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 13px !important;
}

/* Result box - highlighted */
.result-box textarea {
    background: #0d1226 !important;
    border: 1px solid #6366f1 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* Accordion */
.gr-accordion {
    background: #111827 !important;
    border: 1px solid #1e2a45 !important;
    border-radius: 10px !important;
}

/* Labels */
label span {
    color: #94a3b8 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* Tabs */
.gr-tab-nav button {
    background: transparent !important;
    color: #64748b !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 500 !important;
}
.gr-tab-nav button.selected {
    color: #6366f1 !important;
    border-bottom-color: #6366f1 !important;
}

/* Status bar */
.status-bar {
    background: #0d1226;
    border: 1px solid #1e2a45;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 12px;
    color: #64748b;
    display: flex;
    justify-content: space-between;
}

/* Quick commands */
.quick-cmd {
    background: #1a1f35 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 12px !important;
    padding: 6px 12px !important;
    cursor: pointer !important;
    margin: 3px !important;
}
.quick-cmd:hover {
    border-color: #6366f1 !important;
    color: #6366f1 !important;
}
"""

HEADER_HTML = """
<div class="aether-header">
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:10px;">
        <span style="font-size:32px;">🛡️</span>
        <div>
            <h1 style="margin:0; font-family:'Space Grotesk',sans-serif; font-size:26px; font-weight:700; color:#e2e8f0; letter-spacing:-0.02em;">
                Aether Concierge
            </h1>
            <p style="margin:4px 0 0; font-size:13px; color:#64748b; font-weight:400;">
                Privacy-First Personal Life Agent · Powered by Gemini 2.5 Flash
            </p>
        </div>
    </div>
    <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
        <span style="background:#1e3a5f; color:#60a5fa; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">✅ TASKS</span>
        <span style="background:#1e3a2f; color:#34d399; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">💊 HEALTH</span>
        <span style="background:#3a1e3f; color:#c084fc; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">🎉 EVENTS</span>
        <span style="background:#1e3a1e; color:#86efac; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">🌱 GARDEN</span>
        <span style="background:#2a1e1e; color:#f87171; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">🛡️ PRIVACY</span>
    </div>
</div>
"""

QUICK_COMMANDS = [
    "Add task: Buy groceries tomorrow",
    "Log medication: Vitamin D 1000mg every morning",
    "Plan birthday party for next Saturday",
    "Add tomato plant to garden",
    "Show all my tasks",
    "List health summary",
    "Show upcoming events",
    "Show garden status",
]

def fill_command(cmd):
    return cmd

if __name__ == "__main__":
    ensure_sandbox()

    with gr.Blocks(title="Aether Concierge") as demo:

        # Header
        gr.HTML(HEADER_HTML)

        with gr.Tabs():

            # ---- MAIN AGENT TAB ----
            with gr.Tab("🚀 Agent"):
                with gr.Row():
                    with gr.Column(scale=3):
                        user_input = gr.Textbox(
                            label="Enter Command",
                            placeholder='e.g. "Add task: Call doctor tomorrow at 3pm" or "Plan a garden party for 10 guests"',
                            lines=2,
                            elem_classes=["card"]
                        )
                        with gr.Row():
                            submit_btn = gr.Button(
                                "✨ Execute Agent Pipeline",
                                variant="primary",
                                elem_classes=["primary-btn"]
                            )
                            clear_btn = gr.Button("🗑️ Clear", elem_classes=["secondary-btn"])

                    with gr.Column(scale=2):
                        dashboard = gr.Textbox(
                            label="📊 Dashboard",
                            value=get_dashboard_summary(),
                            lines=10,
                            interactive=False,
                            elem_classes=["output-box"]
                        )

                # Quick commands
                gr.HTML("<p style='color:#64748b; font-size:12px; margin:8px 0 6px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>⚡ Quick Commands</p>")
                with gr.Row():
                    for cmd in QUICK_COMMANDS[:4]:
                        qb = gr.Button(cmd, elem_classes=["quick-cmd"])
                        qb.click(fn=lambda c=cmd: c, outputs=user_input)
                with gr.Row():
                    for cmd in QUICK_COMMANDS[4:]:
                        qb = gr.Button(cmd, elem_classes=["quick-cmd"])
                        qb.click(fn=lambda c=cmd: c, outputs=user_input)

                # Pipeline output
                gr.HTML("<hr style='border-color:#1e2a45; margin:16px 0;'>")
                gr.HTML("<p style='color:#64748b; font-size:12px; margin:0 0 10px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>🔍 Agent Pipeline Output</p>")

                with gr.Row():
                    out_privacy = gr.Textbox(
                        label="🛡️ Node A: Privacy Analyst (Sanitized)",
                        lines=2,
                        interactive=False,
                        elem_classes=["output-box"]
                    )
                    out_action = gr.Textbox(
                        label="🧠 Node B: Logic Engine (Domain → Action)",
                        lines=2,
                        interactive=False,
                        elem_classes=["output-box"]
                    )

                out_result = gr.Textbox(
                    label="⚡ Node C: Physical Executor (Result)",
                    lines=3,
                    interactive=False,
                    elem_classes=["result-box"]
                )

                out_message = gr.Textbox(
                    label="💬 Aether Says",
                    lines=2,
                    interactive=False,
                    elem_classes=["result-box"]
                )

                # Wire buttons
                def run_and_refresh(cmd):
                    p, a, r, m = run_agent_pipeline(cmd)
                    dash = get_dashboard_summary()
                    return p, a, r, m, dash

                submit_btn.click(
                    fn=run_and_refresh,
                    inputs=user_input,
                    outputs=[out_privacy, out_action, out_result, out_message, dashboard]
                )
                clear_btn.click(
                    fn=lambda: ("", "", "", "", get_dashboard_summary()),
                    outputs=[out_privacy, out_action, out_result, out_message, dashboard]
                )
                user_input.submit(
                    fn=run_and_refresh,
                    inputs=user_input,
                    outputs=[out_privacy, out_action, out_result, out_message, dashboard]
                )

            # ---- MEMORY TAB ----
            with gr.Tab("🧠 Memory"):
                gr.HTML("<p style='color:#94a3b8; margin-bottom:16px;'>Set permanent rules that Aether will always follow. These persist across sessions.</p>")
                memory_display = gr.Textbox(
                    label="📖 Current Memory Rules",
                    value=get_memory_display(),
                    lines=6,
                    interactive=False,
                    elem_classes=["output-box"]
                )
                with gr.Row():
                    memory_input = gr.Textbox(
                        label="New Rule",
                        placeholder='e.g. "Always classify work tasks under TASKS" or "Garden tasks due on Sundays"',
                        elem_classes=["card"]
                    )
                    save_btn = gr.Button("💾 Save Rule", variant="primary", elem_classes=["primary-btn"])

                mem_status = gr.Textbox(label="Status", interactive=False, elem_classes=["output-box"])

                def save_and_refresh(rule):
                    msg = save_memory(rule)
                    return msg, get_memory_display()

                save_btn.click(
                    fn=save_and_refresh,
                    inputs=memory_input,
                    outputs=[mem_status, memory_display]
                )

            # ---- VIEW DATA TAB ----
            with gr.Tab("📁 My Data"):
                gr.HTML("<p style='color:#94a3b8; margin-bottom:16px;'>View all your stored data across all domains.</p>")

                with gr.Row():
                    view_tasks_btn = gr.Button("📋 View Tasks", elem_classes=["secondary-btn"])
                    view_health_btn = gr.Button("💊 View Health", elem_classes=["secondary-btn"])
                    view_events_btn = gr.Button("🎉 View Events", elem_classes=["secondary-btn"])
                    view_garden_btn = gr.Button("🌱 View Garden", elem_classes=["secondary-btn"])

                data_output = gr.Textbox(
                    label="Data Viewer",
                    lines=15,
                    interactive=False,
                    elem_classes=["output-box"]
                )

                def view_domain(domain):
                    _, _, result, _ = run_agent_pipeline(f"List {domain}")
                    return result

                view_tasks_btn.click(fn=lambda: "\n".join(get_tasks()) or "No tasks yet.", outputs=data_output)
                view_health_btn.click(fn=lambda: execute_action({"action": "LIST_HEALTH", "extracted_data": {}}), outputs=data_output)
                view_events_btn.click(fn=lambda: execute_action({"action": "LIST_EVENTS", "extracted_data": {}}), outputs=data_output)
                view_garden_btn.click(fn=lambda: execute_action({"action": "LIST_GARDEN", "extracted_data": {}}), outputs=data_output)

            # ---- ABOUT TAB ----
            with gr.Tab("ℹ️ About"):
                gr.HTML("""
                <div style="color:#94a3b8; line-height:1.8; max-width:700px;">
                    <h2 style="color:#e2e8f0; font-family:'Space Grotesk',sans-serif;">🛡️ Aether Concierge</h2>
                    <p><strong style="color:#6366f1;">Privacy-First Multi-Agent Architecture</strong></p>
                    
                    <h3 style="color:#c084fc; margin-top:20px;">Architecture</h3>
                    <ul>
                        <li><strong>Node A</strong> — Privacy Analyst: Sanitizes sensitive data before any processing</li>
                        <li><strong>Node B</strong> — Logic Engine: Classifies intent into domain + action (12 action types)</li>
                        <li><strong>Node C</strong> — Physical Executor: Runs actions locally with zero extra API calls</li>
                    </ul>
                    
                    <h3 style="color:#34d399; margin-top:20px;">Domains Handled</h3>
                    <ul>
                        <li>✅ <strong>Tasks</strong> — Daily to-dos, reminders, personal notes</li>
                        <li>💊 <strong>Health</strong> — Medications, doctor appointments, health tracking</li>
                        <li>🎉 <strong>Events</strong> — Party planning, guest lists, family gatherings</li>
                        <li>🌱 <strong>Garden</strong> — Plant tracking, garden tasks, home planning</li>
                    </ul>
                    
                    <h3 style="color:#60a5fa; margin-top:20px;">Privacy Features</h3>
                    <ul>
                        <li>🔒 All data stored locally on your machine only</li>
                        <li>🛡️ Automatic redaction of passwords, banking info, SSNs</li>
                        <li>⛔ Security gate blocks dangerous commands</li>
                        <li>📊 Analytics ledger stored locally as CSV</li>
                    </ul>
                    
                    <h3 style="color:#f59e0b; margin-top:20px;">Quota Optimization</h3>
                    <p>Designed for free tier: <strong>1 API call per user request</strong> 
                    (vs 3 calls in traditional pipelines). Uses Gemini 2.5 Flash.</p>
                    
                    <p style="margin-top:20px; font-size:12px; color:#475569;">
                        Built for Google x Kaggle 5-Day AI Agents Intensive — Capstone Project 2026
                    </p>
                </div>
                """)

        # Footer
        gr.HTML("""
        <div style="text-align:center; padding:16px; color:#334155; font-size:12px; border-top:1px solid #1e2a45; margin-top:20px;">
            🛡️ Aether Concierge · Privacy-First · All data stays on your device · 
            Built with Gradio + Gemini 2.5 Flash
        </div>
        """)

    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, css=CUSTOM_CSS)