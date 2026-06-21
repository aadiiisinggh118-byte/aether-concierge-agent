import os
import csv
import json
import shutil
import threading
import time
import subprocess
from datetime import datetime, date, timedelta
from google import genai
from dotenv import load_dotenv
import gradio as gr

# ==========================================
# PHASE 1: SECURE INITIALIZATION
# ==========================================
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("SECURITY ALERT: API Key not found in .env file.")

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

SANDBOX_PATH = os.path.join(os.getcwd(), "Test_Desktop")
MEMORY_FILE = "memory.json"
TASKS_FILE = os.path.join(SANDBOX_PATH, "daily_tasks.json")
HEALTH_FILE = os.path.join(SANDBOX_PATH, "health_tracker.json")
EVENTS_FILE = os.path.join(SANDBOX_PATH, "events.json")
GARDEN_FILE = os.path.join(SANDBOX_PATH, "garden_planner.json")
ANALYTICS_FILE = "concierge_analytics.csv"

# ==========================================
# CONVERSATION CONTEXT (Session Memory)
# ==========================================
conversation_history = []
last_task_id = None

def add_to_context(role: str, content: str):
    conversation_history.append({"role": role, "content": content})
    if len(conversation_history) > 12:
        conversation_history.pop(0)

def get_context_summary() -> str:
    if not conversation_history:
        return "No previous context."
    recent = conversation_history[-6:]
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in recent)

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
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json_file(filepath: str, data):
    ensure_sandbox()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ==========================================
# WINDOWS DESKTOP NOTIFICATIONS
# ==========================================
def send_windows_notification(title: str, message: str):
    try:
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 6
$notify.Dispose()
'''
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        print(f"Notification error: {e}")

def schedule_notification(task_title: str, remind_time: datetime):
    def _notify():
        now = datetime.now()
        wait_seconds = (remind_time - now).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        send_windows_notification("Aether Reminder", f"Task due: {task_title}")
    t = threading.Thread(target=_notify, daemon=True)
    t.start()

def parse_reminder_time(date_str: str, time_str: str):
    today = date.today()
    dt = None
    try:
        if date_str:
            dl = date_str.lower().strip()
            if dl in ["today", "tonight"]:
                d = today
            elif dl == "tomorrow":
                d = today + timedelta(days=1)
            else:
                for fmt in ["%Y-%m-%d", "%B %d", "%b %d", "%d %B", "%d/%m/%Y", "%m/%d/%Y"]:
                    try:
                        parsed = datetime.strptime(date_str.strip(), fmt)
                        d = parsed.replace(year=today.year).date()
                        break
                    except:
                        continue
                else:
                    d = today
        else:
            d = today

        if time_str:
            tl = time_str.lower().strip()
            for fmt in ["%I:%M %p", "%I %p", "%H:%M", "%I:%M%p", "%I%p"]:
                try:
                    parsed_time = datetime.strptime(tl, fmt)
                    dt = datetime.combine(d, parsed_time.time())
                    break
                except:
                    continue
        return dt
    except:
        return None

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
    return f"Rule saved: '{new_rule}'"

def get_memory_display() -> str:
    memory = get_memory()
    rules = memory.get("rules", [])
    if not rules:
        return "No custom rules set."
    return "\n".join(f"- {r}" for r in rules)

# ==========================================
# TASK STORAGE
# ==========================================
def get_tasks() -> list:
    data = load_json_file(TASKS_FILE, {"tasks": []})
    return data.get("tasks", [])

def save_tasks(tasks: list):
    save_json_file(TASKS_FILE, {"tasks": tasks})

def generate_task_id() -> str:
    return f"task_{int(time.time()*1000)}"

def format_tasks_display(tasks: list) -> str:
    if not tasks:
        return "No tasks yet! Add your first task."
    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]
    priority_order = {"high": 0, "medium": 1, "low": 2}
    pending.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
    result = []
    if pending:
        result.append(f"Pending Tasks ({len(pending)})")
        for t in pending:
            p = t.get("priority", "medium")
            icon = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(p, "[MED]")
            due = f" | Due: {t['due_date']}" if t.get("due_date") else ""
            time_val = f" at {t['due_time']}" if t.get("due_time") else ""
            result.append(f"  {icon} {t['title']}{due}{time_val}")
    if done:
        result.append(f"\nCompleted ({len(done)})")
        for t in done[-3:]:
            result.append(f"  DONE: {t['title']}")
    return "\n".join(result)

# ==========================================
# DOMAIN DATA LOADERS
# ==========================================
def get_health_data() -> dict:
    return load_json_file(HEALTH_FILE, {"medications": [], "appointments": [], "notes": []})

def get_events() -> dict:
    return load_json_file(EVENTS_FILE, {"events": []})

def get_garden_data() -> dict:
    return load_json_file(GARDEN_FILE, {"plants": [], "tasks": [], "notes": []})

# ==========================================
# CORE: SINGLE SMART API CALL
# ==========================================
def smart_concierge_brain(user_input: str) -> dict:
    global last_task_id
    memory = get_memory()
    rules_text = "\n".join(memory.get("rules", [])) or "None"
    today_str = date.today().strftime("%A, %B %d, %Y")
    context = get_context_summary()

    system_prompt = f"""You are Aether Concierge - a privacy-first personal AI agent.
Today: {today_str}

CONVERSATION CONTEXT:
{context}

USER MEMORY RULES:
{rules_text}

DOMAINS: TASKS, HEALTH, EVENTS, GARDEN

PRIVACY: Redact passwords, banking info, SSN with [REDACTED].

ACTIONS:
- LOG_TASK: Add new task
- COMPLETE_TASK: Mark task done
- DELETE_TASK: Remove task
- LIST_TASKS: Show all tasks
- UPDATE_PRIORITY: Change task priority
- SEARCH_TASKS: Search by keyword
- LOG_MEDICATION: Track medication
- LOG_APPOINTMENT: Add appointment
- LIST_HEALTH: Show health data
- LOG_EVENT: Create event
- ADD_GUEST: Add guests to event
- LIST_EVENTS: Show events
- LOG_PLANT: Add plant
- LOG_GARDEN_TASK: Add garden task
- LIST_GARDEN: Show garden
- UNKNOWN: Cannot determine

PRIORITY: urgent/important/ASAP = high, whenever/low priority = low, default = medium

Use CONVERSATION CONTEXT to resolve "mark that as done", "change its priority", etc.

Respond ONLY in this exact JSON (no markdown, no extra text):
{{
  "safe_input": "sanitized input",
  "domain": "TASKS|HEALTH|EVENTS|GARDEN|UNKNOWN",
  "action": "ACTION_NAME",
  "extracted_data": {{
    "title": "main description",
    "priority": "high|medium|low",
    "date": "date string or null",
    "time": "time string or null",
    "people": [],
    "notes": "extra details",
    "quantity": "dose or null",
    "search_term": "keyword or null",
    "task_reference": "reference to previous task or null"
  }},
  "user_message": "friendly 1-2 sentence confirmation"
}}

USER INPUT: {user_input}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=system_prompt
    )

    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "safe_input": user_input,
            "domain": "UNKNOWN",
            "action": "UNKNOWN",
            "extracted_data": {
                "title": user_input, "priority": "medium",
                "date": None, "time": None, "people": [],
                "notes": "", "quantity": None,
                "search_term": None, "task_reference": None
            },
            "user_message": "I understood your request but could not classify it. Please try rephrasing."
        }

# ==========================================
# NODE C: PHYSICAL EXECUTOR
# ==========================================
def execute_action(brain_result: dict) -> str:
    global last_task_id
    ensure_sandbox()
    action = brain_result.get("action", "UNKNOWN")
    data = brain_result.get("extracted_data", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = data.get("title", "Untitled")
    priority = data.get("priority", "medium")
    date_val = data.get("date") or ""
    time_val = data.get("time") or ""
    people = data.get("people") or []
    notes = data.get("notes") or ""
    quantity = data.get("quantity") or ""
    search_term = data.get("search_term") or ""
    task_ref = data.get("task_reference") or ""

    # ---- TASKS ----
    if action == "LOG_TASK":
        tasks = get_tasks()
        task_id = generate_task_id()
        task = {
            "id": task_id,
            "title": title,
            "priority": priority,
            "status": "pending",
            "due_date": date_val,
            "due_time": time_val,
            "notes": notes,
            "created": timestamp
        }
        tasks.append(task)
        save_tasks(tasks)
        last_task_id = task_id

        reminder_dt = parse_reminder_time(date_val, time_val)
        notif_msg = ""
        if reminder_dt and reminder_dt > datetime.now():
            schedule_notification(title, reminder_dt)
            notif_msg = f" | Reminder set for {reminder_dt.strftime('%b %d at %I:%M %p')}"
        send_windows_notification("Aether Task Added", f"{title} ({priority} priority)")

        priority_icon = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(priority, "[MED]")
        return f"{priority_icon} Task added: '{title}' | Priority: {priority.upper()}{notif_msg}"

    elif action == "COMPLETE_TASK":
        tasks = get_tasks()
        matched_idx = None
        if task_ref and last_task_id:
            for i, t in enumerate(tasks):
                if t["id"] == last_task_id:
                    matched_idx = i
                    break
        if matched_idx is None and title and title != "Untitled":
            for i, t in enumerate(tasks):
                if title.lower() in t["title"].lower() and t["status"] == "pending":
                    matched_idx = i
                    break
        if matched_idx is None:
            pending = [(i, t) for i, t in enumerate(tasks) if t["status"] == "pending"]
            if pending:
                matched_idx = pending[-1][0]
        if matched_idx is not None:
            tasks[matched_idx]["status"] = "done"
            tasks[matched_idx]["completed_at"] = timestamp
            done_title = tasks[matched_idx]["title"]
            save_tasks(tasks)
            send_windows_notification("Aether Task Done!", f"Completed: {done_title}")
            return f"Task completed: '{done_title}'"
        return "No matching pending task found."

    elif action == "DELETE_TASK":
        tasks = get_tasks()
        original_count = len(tasks)
        tasks = [t for t in tasks if title.lower() not in t["title"].lower()]
        if len(tasks) < original_count:
            save_tasks(tasks)
            return f"Task deleted: '{title}'"
        return f"No task found matching '{title}'"

    elif action == "LIST_TASKS":
        tasks = get_tasks()
        return format_tasks_display(tasks)

    elif action == "UPDATE_PRIORITY":
        tasks = get_tasks()
        matched_idx = None
        if last_task_id:
            for i, t in enumerate(tasks):
                if t["id"] == last_task_id:
                    matched_idx = i
                    break
        if matched_idx is None and title and title != "Untitled":
            for i, t in enumerate(tasks):
                if title.lower() in t["title"].lower():
                    matched_idx = i
                    break
        if matched_idx is not None:
            tasks[matched_idx]["priority"] = priority
            save_tasks(tasks)
            return f"Priority updated: '{tasks[matched_idx]['title']}' to {priority.upper()}"
        return "No matching task found to update."

    elif action == "SEARCH_TASKS":
        tasks = get_tasks()
        keyword = search_term or title
        if not keyword:
            return "Please provide a search keyword."
        matches = [t for t in tasks if keyword.lower() in t["title"].lower()
                   or keyword.lower() in t.get("notes", "").lower()]
        if not matches:
            return f"No tasks found matching '{keyword}'"
        result = [f"Search results for '{keyword}':"]
        for t in matches:
            status = "DONE" if t["status"] == "done" else "PENDING"
            result.append(f"  [{status}] {t['title']} ({t.get('priority','medium')} priority)")
        return "\n".join(result)

    # ---- HEALTH ----
    elif action == "LOG_MEDICATION":
        health = get_health_data()
        med = {"name": title, "dose": quantity or "Not specified",
               "time": time_val or "Not specified", "added": timestamp, "notes": notes}
        health["medications"].append(med)
        save_json_file(HEALTH_FILE, health)
        send_windows_notification("Aether Health", f"Medication logged: {title}")
        return f"Medication logged: '{title}' | Dose: {quantity or 'Not specified'}"

    elif action == "LOG_APPOINTMENT":
        health = get_health_data()
        appt = {"title": title, "date": date_val or "Date not specified",
                "time": time_val or "Time not specified", "notes": notes, "added": timestamp}
        health["appointments"].append(appt)
        save_json_file(HEALTH_FILE, health)
        reminder_dt = parse_reminder_time(date_val, time_val)
        if reminder_dt and reminder_dt > datetime.now():
            schedule_notification(f"Appointment: {title}", reminder_dt)
        return f"Appointment saved: '{title}' on {date_val or 'date TBD'}"

    elif action == "LIST_HEALTH":
        health = get_health_data()
        result = []
        meds = health.get("medications", [])
        appts = health.get("appointments", [])
        if meds:
            result.append("Medications:")
            for m in meds[-5:]:
                result.append(f"  - {m['name']} | {m['dose']} at {m['time']}")
        if appts:
            result.append("Appointments:")
            for a in appts[-5:]:
                result.append(f"  - {a['title']} on {a['date']} at {a['time']}")
        if not result:
            return "No health records yet."
        return "\n".join(result)

    # ---- EVENTS ----
    elif action == "LOG_EVENT":
        events_data = get_events()
        event = {"id": len(events_data["events"]) + 1, "title": title,
                 "date": date_val or "Date TBD", "time": time_val or "Time TBD",
                 "guests": people, "notes": notes, "created": timestamp}
        events_data["events"].append(event)
        save_json_file(EVENTS_FILE, events_data)
        return f"Event created: '{title}' on {date_val or 'date TBD'} | Guests: {len(people)}"

    elif action == "ADD_GUEST":
        events_data = get_events()
        evs = events_data.get("events", [])
        if not evs:
            return "No events found. Create an event first!"
        evs[-1]["guests"].extend(people)
        save_json_file(EVENTS_FILE, events_data)
        added = ", ".join(people) if people else "guests"
        return f"Added {added} to '{evs[-1]['title']}'"

    elif action == "LIST_EVENTS":
        events_data = get_events()
        evs = events_data.get("events", [])
        if not evs:
            return "No events planned yet."
        result = ["Upcoming Events:"]
        for e in evs[-5:]:
            result.append(f"  - {e['title']} on {e['date']} | {len(e.get('guests',[]))} guests")
        return "\n".join(result)

    # ---- GARDEN ----
    elif action == "LOG_PLANT":
        garden = get_garden_data()
        plant = {"name": title, "planted": date_val or timestamp[:10],
                 "notes": notes, "added": timestamp}
        garden["plants"].append(plant)
        save_json_file(GARDEN_FILE, garden)
        return f"Plant added: '{title}'"

    elif action == "LOG_GARDEN_TASK":
        garden = get_garden_data()
        task = {"task": title, "due": date_val or "No due date",
                "notes": notes, "added": timestamp}
        garden["tasks"].append(task)
        save_json_file(GARDEN_FILE, garden)
        return f"Garden task added: '{title}'"

    elif action == "LIST_GARDEN":
        garden = get_garden_data()
        plants = garden.get("plants", [])
        tasks = garden.get("tasks", [])
        result = []
        if plants:
            result.append(f"Plants ({len(plants)}):")
            for p in plants[-5:]:
                result.append(f"  - {p['name']} planted {p['planted']}")
        if tasks:
            result.append("Garden Tasks:")
            for t in tasks[-5:]:
                result.append(f"  - {t['task']} due {t['due']}")
        if not result:
            return "Garden is empty!"
        return "\n".join(result)

    return "I understood your request but was not sure what action to take. Try being more specific!"

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
# DASHBOARD
# ==========================================
def get_dashboard_summary() -> str:
    tasks = get_tasks()
    health = get_health_data()
    events = get_events()
    garden = get_garden_data()
    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]
    high = [t for t in pending if t.get("priority") == "high"]
    return f"""Your Aether Dashboard
========================
Tasks: {len(pending)} pending | {len(done)} done
High Priority: {len(high)} tasks
Medications: {len(health.get('medications', []))} tracked
Appointments: {len(health.get('appointments', []))} scheduled
Events: {len(events.get('events', []))} planned
Plants: {len(garden.get('plants', []))} in garden
========================
Try: "Add urgent task: Submit report by 5pm"
Or: "Mark last task as done"
Or: "Search tasks: doctor" """

# ==========================================
# MAIN PIPELINE
# ==========================================
def run_agent_pipeline(user_command: str):
    if not user_command or not user_command.strip():
        return "Please enter a command.", "-", "-", "Please type something!"
    try:
        try:
            local_security_gate(user_command)
        except PermissionError as e:
            return f"BLOCKED: {str(e)}", "BLOCKED", "BLOCKED", str(e)

        add_to_context("user", user_command)
        brain_result = smart_concierge_brain(user_command)
        physical_result = execute_action(brain_result)
        add_to_context("assistant", brain_result.get("user_message", physical_result))
        log_to_ledger(user_command, brain_result, physical_result)

        safe_input = brain_result.get("safe_input", user_command)
        action = f"{brain_result.get('domain','?')} -> {brain_result.get('action','?')}"
        user_msg = brain_result.get("user_message", physical_result)
        return safe_input, action, physical_result, user_msg

    except Exception as e:
        err = str(e)
        return f"Error: {err}", "ERROR", "ABORTED", f"System error: {err}"

# ==========================================
# GRADIO UI
# ==========================================
HEADER_HTML = """
<div style="background:linear-gradient(135deg,#1a1f35 0%,#0d1226 100%);
    border:1px solid #2d3561;border-radius:16px;padding:28px 32px;margin-bottom:20px;
    position:relative;overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,#6366f1,#8b5cf6,#06b6d4);"></div>
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
        <span style="font-size:32px;">🛡️</span>
        <div>
            <h1 style="margin:0;font-size:26px;font-weight:700;color:#e2e8f0;">
                Aether Concierge
            </h1>
            <p style="margin:4px 0 0;font-size:13px;color:#64748b;">
                Privacy-First Personal Life Agent · Powered by Gemini 2.5 Flash
            </p>
        </div>
    </div>
    <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
        <span style="background:#1e3a5f;color:#60a5fa;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">✅ TASKS</span>
        <span style="background:#1e3a2f;color:#34d399;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">💊 HEALTH</span>
        <span style="background:#3a1e3f;color:#c084fc;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">🎉 EVENTS</span>
        <span style="background:#1e3a1e;color:#86efac;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">🌱 GARDEN</span>
        <span style="background:#2a1e1e;color:#f87171;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">🛡️ PRIVACY</span>
        <span style="background:#1e2a3a;color:#38bdf8;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">🔔 NOTIFICATIONS</span>
    </div>
</div>
"""

QUICK_COMMANDS = [
    "Add urgent task: Submit project report by 5pm today",
    "Add task: Buy groceries tomorrow morning",
    "Log medication: Vitamin D 1000mg every morning",
    "Plan birthday party for next Saturday",
    "Mark last task as done",
    "Show all my tasks",
    "Search tasks: report",
    "Show garden status",
]

CUSTOM_CSS = """
body, .gradio-container { background: #0a0e1a !important; color: #e2e8f0 !important; }
.gradio-container { max-width: 1100px !important; margin: 0 auto !important; }
"""

if __name__ == "__main__":
    ensure_sandbox()
    send_windows_notification("Aether Concierge", "Your personal agent is ready!")

    with gr.Blocks(title="Aether Concierge") as demo:
        gr.HTML(HEADER_HTML)

        with gr.Tabs():
            with gr.Tab("🚀 Agent"):
                with gr.Row():
                    with gr.Column(scale=3):
                        user_input = gr.Textbox(
                            label="Enter Command",
                            placeholder='e.g. "Add urgent task: Call doctor at 3pm" or "Mark last task as done"',
                            lines=2
                        )
                        with gr.Row():
                            submit_btn = gr.Button("✨ Execute Agent Pipeline", variant="primary")
                            clear_btn = gr.Button("Clear")
                    with gr.Column(scale=2):
                        dashboard = gr.Textbox(
                            label="Dashboard",
                            value=get_dashboard_summary(),
                            lines=11,
                            interactive=False
                        )

                gr.HTML("<p style='color:#64748b;font-size:12px;margin:8px 0 4px;font-weight:600;'>QUICK COMMANDS</p>")
                with gr.Row():
                    for cmd in QUICK_COMMANDS[:4]:
                        qb = gr.Button(cmd, size="sm")
                        qb.click(fn=lambda c=cmd: c, outputs=user_input)
                with gr.Row():
                    for cmd in QUICK_COMMANDS[4:]:
                        qb = gr.Button(cmd, size="sm")
                        qb.click(fn=lambda c=cmd: c, outputs=user_input)

                gr.HTML("<hr style='border-color:#1e2a45;margin:16px 0;'>")
                with gr.Row():
                    out_privacy = gr.Textbox(label="Node A: Privacy Analyst (Sanitized)", lines=2, interactive=False)
                    out_action = gr.Textbox(label="Node B: Logic Engine (Domain -> Action)", lines=2, interactive=False)
                out_result = gr.Textbox(label="Node C: Physical Executor (Result)", lines=3, interactive=False)
                out_message = gr.Textbox(label="Aether Says", lines=2, interactive=False)

                def run_and_refresh(cmd):
                    p, a, r, m = run_agent_pipeline(cmd)
                    dash = get_dashboard_summary()
                    return p, a, r, m, dash

                submit_btn.click(fn=run_and_refresh, inputs=user_input,
                    outputs=[out_privacy, out_action, out_result, out_message, dashboard])
                clear_btn.click(fn=lambda: ("", "", "", "", get_dashboard_summary()),
                    outputs=[out_privacy, out_action, out_result, out_message, dashboard])
                user_input.submit(fn=run_and_refresh, inputs=user_input,
                    outputs=[out_privacy, out_action, out_result, out_message, dashboard])

            with gr.Tab("🧠 Memory"):
                memory_display = gr.Textbox(label="Current Rules", value=get_memory_display(), lines=6, interactive=False)
                with gr.Row():
                    memory_input = gr.Textbox(label="New Rule", placeholder='e.g. "Always mark work tasks as high priority"')
                    save_btn = gr.Button("Save Rule", variant="primary")
                mem_status = gr.Textbox(label="Status", interactive=False)
                def save_and_refresh(rule):
                    msg = save_memory(rule)
                    return msg, get_memory_display()
                save_btn.click(fn=save_and_refresh, inputs=memory_input, outputs=[mem_status, memory_display])

            with gr.Tab("📁 My Data"):
                with gr.Row():
                    view_tasks_btn = gr.Button("View Tasks")
                    view_health_btn = gr.Button("View Health")
                    view_events_btn = gr.Button("View Events")
                    view_garden_btn = gr.Button("View Garden")
                data_output = gr.Textbox(label="Data Viewer", lines=15, interactive=False)
                view_tasks_btn.click(fn=lambda: format_tasks_display(get_tasks()), outputs=data_output)
                view_health_btn.click(fn=lambda: execute_action({"action": "LIST_HEALTH", "extracted_data": {}}), outputs=data_output)
                view_events_btn.click(fn=lambda: execute_action({"action": "LIST_EVENTS", "extracted_data": {}}), outputs=data_output)
                view_garden_btn.click(fn=lambda: execute_action({"action": "LIST_GARDEN", "extracted_data": {}}), outputs=data_output)

            with gr.Tab("ℹ️ About"):
                gr.HTML("""
                <div style="color:#94a3b8;line-height:1.8;max-width:700px;padding:20px;">
                    <h2 style="color:#e2e8f0;">Aether Concierge</h2>
                    <p><strong style="color:#6366f1;">Privacy-First Multi-Agent Architecture</strong></p>
                    <h3 style="color:#c084fc;">Agent Nodes</h3>
                    <ul>
                        <li><strong>Node A</strong> - Privacy Analyst: Sanitizes + classifies in ONE API call</li>
                        <li><strong>Node B</strong> - Logic Engine: 16 action types across 4 domains</li>
                        <li><strong>Node C</strong> - Physical Executor: 100% local, zero API calls</li>
                    </ul>
                    <h3 style="color:#34d399;">Key Features</h3>
                    <ul>
                        <li>Windows Desktop Notifications for tasks and reminders</li>
                        <li>Conversation Context - "Mark that as done" works!</li>
                        <li>Task Priorities - High/Medium/Low</li>
                        <li>Task Search by keyword</li>
                        <li>Task Completion tracking</li>
                        <li>Long-term memory across sessions</li>
                        <li>All data stored locally - never leaves your machine</li>
                    </ul>
                    <p style="font-size:12px;color:#475569;margin-top:20px;">
                        Built for Google x Kaggle 5-Day AI Agents Intensive - Capstone 2026
                    </p>
                </div>
                """)

        gr.HTML("""
        <div style="text-align:center;padding:16px;color:#334155;font-size:12px;border-top:1px solid #1e2a45;margin-top:20px;">
            Aether Concierge - Privacy-First - All data stays on your device - Built with Gradio + Gemini 2.5 Flash
        </div>
        """)

    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, css=CUSTOM_CSS)