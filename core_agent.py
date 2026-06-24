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

def generate_pdf_report() -> str:
    tasks = get_tasks()
    health = get_health_data()
    events = get_events()
    garden = get_garden_data()
    today = date.today().strftime("%B %d, %Y")
    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]

    # Build HTML report
    tasks_html = ""
    for t in pending:
        p = t.get("priority", "medium")
        color = {"high": "#f87171", "medium": "#fbbf24", "low": "#34d399"}.get(p, "#fbbf24")
        tasks_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{t['title']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:{color};font-weight:600;">{p.upper()}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{t.get('due_date','—')}</td>
        </tr>"""

    meds_html = ""
    for m in health.get("medications", []):
        meds_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{m['name']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{m['dose']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{m['time']}</td>
        </tr>"""

    events_html = ""
    for e in events.get("events", []):
        events_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{e['title']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{e['date']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{len(e.get('guests',[]))} guests</td>
        </tr>"""

    plants_html = ""
    for p in garden.get("plants", []):
        plants_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{p['name']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{p['planted']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aether Concierge Report</title>
<style>
    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; color: #1e293b; }}
    h1 {{ color: #6366f1; border-bottom: 3px solid #6366f1; padding-bottom: 10px; }}
    h2 {{ color: #1e293b; margin-top: 30px; font-size: 16px; 
          background: #f1f5f9; padding: 8px 12px; border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th {{ background: #6366f1; color: white; padding: 10px 8px; text-align: left; }}
    .summary {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin: 20px 0; }}
    .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; 
             padding: 16px; text-align: center; }}
    .card-number {{ font-size: 28px; font-weight: 700; color: #6366f1; }}
    .card-label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
    .footer {{ margin-top: 40px; text-align: center; color: #94a3b8; font-size: 12px; 
               border-top: 1px solid #e2e8f0; padding-top: 16px; }}
</style>
</head>
<body>
    <h1>🛡️ Aether Concierge — Personal Report</h1>
    <p style="color:#64748b;">Generated on {today} · All data stored locally on your device</p>

    <div class="summary">
        <div class="card">
            <div class="card-number">{len(pending)}</div>
            <div class="card-label">Pending Tasks</div>
        </div>
        <div class="card">
            <div class="card-number">{len(done)}</div>
            <div class="card-label">Completed Tasks</div>
        </div>
        <div class="card">
            <div class="card-number">{len(health.get('medications',[]))}</div>
            <div class="card-label">Medications</div>
        </div>
        <div class="card">
            <div class="card-number">{len(events.get('events',[]))}</div>
            <div class="card-label">Events Planned</div>
        </div>
    </div>

    <h2>✅ Pending Tasks</h2>
    <table>
        <tr><th>Task</th><th>Priority</th><th>Due Date</th></tr>
        {tasks_html if tasks_html else "<tr><td colspan='3' style='padding:8px;color:#94a3b8;'>No pending tasks</td></tr>"}
    </table>

    <h2>💊 Medications</h2>
    <table>
        <tr><th>Medication</th><th>Dose</th><th>Time</th></tr>
        {meds_html if meds_html else "<tr><td colspan='3' style='padding:8px;color:#94a3b8;'>No medications logged</td></tr>"}
    </table>

    <h2>🎉 Events</h2>
    <table>
        <tr><th>Event</th><th>Date</th><th>Guests</th></tr>
        {events_html if events_html else "<tr><td colspan='3' style='padding:8px;color:#94a3b8;'>No events planned</td></tr>"}
    </table>

    <h2>🌱 Garden</h2>
    <table>
        <tr><th>Plant</th><th>Planted</th></tr>
        {plants_html if plants_html else "<tr><td colspan='2' style='padding:8px;color:#94a3b8;'>No plants logged</td></tr>"}
    </table>

    <div class="footer">
        🛡️ Aether Concierge · Privacy-First · Generated locally · No cloud storage
    </div>
</body>
</html>"""

    # Save report file
    report_path = os.path.join(os.getcwd(), "aether_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Open in browser automatically
    import webbrowser
    webbrowser.open(f"file:///{report_path}")
    return f"✅ Report generated and opened in browser!\nSaved to: {report_path}\n\nYou can print this page as PDF using Ctrl+P → Save as PDF"

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }
body, .gradio-container { background: #0a0e1a !important; color: #e2e8f0 !important; }
.gradio-container { max-width: 1100px !important; margin: 0 auto !important; }

.gr-textbox textarea, .gr-textbox input {
    background: #111827 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 15px !important;
}
.gr-textbox textarea:focus, .gr-textbox input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}
button.primary { 
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; font-size: 15px !important;
}
button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important;
}
button.secondary {
    background: #1e2a45 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
}
.gr-panel, .gr-box {
    background: #111827 !important;
    border: 1px solid #1e2a45 !important;
    border-radius: 12px !important;
}
label span {
    color: #94a3b8 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
.gr-tab-nav button { 
    color: #64748b !important; 
    font-weight: 500 !important;
}
.gr-tab-nav button.selected { 
    color: #6366f1 !important;
    border-bottom: 2px solid #6366f1 !important;
}
.gr-textbox {
    background: #0d1226 !important;
    border: 1px solid #1e2a45 !important;
    border-radius: 10px !important;
}
textarea {
    background: #0d1226 !important;
    color: #e2e8f0 !important;
}
.gradio-container {
    min-width: 100% !important;
    max-width: 100% !important;
    padding: 0 20px !important;
}
.gr-block.gr-box {
    background: #111827 !important;
    border: 1px solid #1e2a45 !important;
    border-radius: 12px !important;
}
"""
# ==========================================
# GUARDIAN MODE - AUTONOMOUS MONITOR
# Runs every 60 mins in background
# No user input needed - truly autonomous
# ==========================================

guardian_status = {
    "active": False,
    "last_check": None,
    "alerts": [],
    "risk_level": "LOW"
}

def run_guardian_monitor():
    """
    Autonomous background agent that monitors user's life
    and proactively sends alerts without user asking.
    This is what makes Aether a TRUE agent, not just a tool.
    """
    import time
    guardian_status["active"] = True
    
    while True:
        alerts = []
        risks = []
        now = datetime.now()
        today = date.today()
        
        # ── CHECK 1: Missed Medications ──
        health = get_health_data()
        meds = health.get("medications", [])
        morning_meds = [m for m in meds if "morning" in m.get("time","").lower()]
        if morning_meds and now.hour >= 10:
            for med in morning_meds:
                alert = f"MISSED DOSE: {med['name']} {med['dose']} — not confirmed today!"
                alerts.append(alert)
                risks.append("HEALTH")
                send_windows_notification(
                    "💊 Aether Health Guardian",
                    f"Missed medication: {med['name']} {med['dose']}"
                )

        # ── CHECK 2: Overdue High Priority Tasks ──
        tasks = get_tasks()
        for t in tasks:
            if t.get("status") != "pending":
                continue
            if t.get("priority") != "high":
                continue
            due = t.get("due_date", "")
            if not due:
                continue
            try:
                due_date = datetime.strptime(due[:10], "%Y-%m-%d").date()
                days_overdue = (today - due_date).days
                if days_overdue >= 2:
                    alert = f"CRITICAL: '{t['title']}' is {days_overdue} days overdue!"
                    alerts.append(alert)
                    risks.append("TASK")
                    send_windows_notification(
                        "🔴 Aether Task Guardian",
                        f"CRITICAL: {t['title']} is {days_overdue} days overdue!"
                    )
            except:
                continue

        # ── CHECK 3: Events in next 24 hours ──
        events_data = get_events()
        for e in events_data.get("events", []):
            try:
                event_date_str = e.get("date", "")
                for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
                    try:
                        event_date = datetime.strptime(
                            event_date_str[:12].strip(), fmt
                        ).date()
                        break
                    except:
                        continue
                days_until = (event_date - today).days
                if days_until == 1:
                    alert = f"EVENT TOMORROW: {e['title']}!"
                    alerts.append(alert)
                    send_windows_notification(
                        "🎉 Aether Event Guardian",
                        f"Reminder: {e['title']} is tomorrow!"
                    )
                elif days_until == 0:
                    alert = f"EVENT TODAY: {e['title']}!"
                    alerts.append(alert)
                    send_windows_notification(
                        "🎉 Aether Event Guardian",
                        f"TODAY: {e['title']} is happening today!"
                    )
            except:
                continue

        # ── CHECK 4: Advanced Health Pattern + Auto Decision Engine ──
        if len(meds) > 0:
            missed_count = len([a for a in alerts if "MISSED" in a])
            
            if missed_count > 0:
                risks.append("HEALTH_PATTERN")
                
                # Read analytics to count historical misses
                historical_misses = 0
                if os.path.isfile(ANALYTICS_FILE):
                    with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if "MISSED" in row.get("Result", ""):
                                historical_misses += 1

                # Calculate adherence %
                total_days = max(historical_misses + 1, 1)
                adherence = max(0, 100 - (historical_misses / total_days * 100))
                adherence = round(adherence, 1)

                alert = (
                    f"HEALTH PATTERN: Medication adherence {adherence}% "
                    f"— {historical_misses} miss(es) detected in history"
                )
                alerts.append(alert)

                # ── AUTO DECISION ENGINE ──
                # If missed 3+ times → automatically create doctor task
                if historical_misses >= 3:
                    existing_tasks = get_tasks()
                    doctor_exists = any(
                        "doctor" in t["title"].lower() and
                        t["status"] == "pending"
                        for t in existing_tasks
                    )
                    if not doctor_exists:
                        # Auto-create doctor appointment task
                        new_task = {
                            "id": f"guardian_{int(time.time()*1000)}",
                            "title": "GUARDIAN ALERT: Schedule doctor visit — medication adherence low",
                            "priority": "high",
                            "status": "pending",
                            "due_date": (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
                            "due_time": "",
                            "notes": f"Auto-created by Guardian. Adherence: {adherence}%. Missed {historical_misses} time(s).",
                            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        existing_tasks.append(new_task)
                        save_tasks(existing_tasks)
                        alerts.append(
                            f"AUTO ACTION: Guardian created doctor visit task "
                            f"(adherence dropped to {adherence}%)"
                        )
                        send_windows_notification(
                            "🤖 Aether Auto-Action",
                            f"Guardian created: Schedule doctor visit (adherence {adherence}%)"
                        )

                # If missed 2+ times → escalate risk
                if historical_misses >= 2:
                    alerts.append(
                        f"RISK ESCALATION: Medication adherence {adherence}% "
                        f"— recommend immediate attention"
                    )
                    send_windows_notification(
                        "🔴 Aether Risk Escalation",
                        f"Health risk escalated! Adherence: {adherence}%. Please take action."
                    )

        # ── UPDATE STATUS ──
        guardian_status["last_check"] = now.strftime("%Y-%m-%d %H:%M:%S")
        guardian_status["alerts"] = alerts
        guardian_status["risk_level"] = (
            "HIGH" if "HEALTH" in risks or len(alerts) >= 3
            else "MEDIUM" if risks
            else "LOW"
        )

        # ── AUTO MORNING BRIEFING at 9am ──
        if now.hour == 9 and now.minute < 5:
            import urllib.request
            try:
                url = "http://127.0.0.1:8765/generate_daily_briefing"
                with urllib.request.urlopen(url, timeout=5) as response:
                    result = json.loads(response.read().decode())
                send_windows_notification(
                    "🌅 Aether Morning Briefing",
                    result["briefing"][:200]
                )
            except:
                pass

        # Wait 60 minutes before next check
        time.sleep(3600)


def get_guardian_report() -> str:
    """Generate caregiver/guardian report showing full status."""
    if not guardian_status["active"]:
        return "Guardian Mode is not active. Restart the app."

    tasks = get_tasks()
    health = get_health_data()
    events = get_events()

    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]
    high = [t for t in pending if t.get("priority") == "high"]
    meds = health.get("medications", [])
    appts = health.get("appointments", [])

    risk = guardian_status["risk_level"]
    risk_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "🟢")
    alerts = guardian_status["alerts"]
    last_check = guardian_status["last_check"] or "Not yet"

    report = f"""🛡️ AETHER GUARDIAN REPORT
Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
Last Monitor Check: {last_check}

{risk_color} RISK LEVEL: {risk}
━━━━━━━━━━━━━━━━━━━━━━

⚠️ ACTIVE ALERTS ({len(alerts)}):
"""
    if alerts:
        for a in alerts:
            report += f"  • {a}\n"
    else:
        report += "  ✅ No active alerts!\n"

    report += f"""
━━━━━━━━━━━━━━━━━━━━━━
📋 TASKS STATUS:
  • Pending: {len(pending)} tasks
  • High Priority: {len(high)} tasks
  • Completed Today: {len(done)} tasks

💊 HEALTH STATUS:
  • Medications Tracked: {len(meds)}
  • Appointments: {len(appts)}

🎉 EVENTS:
  • Upcoming: {len(events.get('events', []))} events
━━━━━━━━━━━━━━━━━━━━━━
🔌 Monitored by Aether Guardian (checks every 60 min)
🛡️ All data stored locally — privacy first"""

    return report

if __name__ == "__main__":
    ensure_sandbox()
    
    # Start MCP server in background thread
    import threading
    from mcp_server import run_mcp_server
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()
    # Start Guardian Monitor in background
    guardian_thread = threading.Thread(target=run_guardian_monitor, daemon=True)
    guardian_thread.start()
    print("[Aether] Guardian Monitor started — checking every 60 minutes")
    print("[Aether] MCP Server started on port 8765")
    
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

                # MCP Daily Briefing
                gr.HTML("<hr style='border-color:#1e2a45;margin:12px 0;'>")
                briefing_btn = gr.Button("🌅 Get Daily Briefing (MCP)", variant="secondary")
                briefing_output = gr.Textbox(label="🤖 MCP Daily Briefing", lines=6, interactive=False)

                def run_daily_briefing():
        # Connect to REAL MCP server via HTTP
                    import urllib.request
                    try:
                        url = "http://127.0.0.1:8765/generate_daily_briefing"
                        with urllib.request.urlopen(url, timeout=5) as response:
                            result = json.loads(response.read().decode())
                    except Exception as e:
                        return f"MCP Server not running. Start it with: python mcp_server.py\nError: {e}"
                    
                    briefing = result["briefing"]
                    s = result["summary"]
                    return f"""{briefing}

                ━━━━━━━━━━━━━━━━━━━━━━
                📊 Summary:
                ✅ Pending Tasks: {s['pending_tasks']}
                🔴 High Priority: {s['high_priority']}
                ⚠️ Overdue: {s['overdue']}
                💊 Medications Today: {s['medications_today']}
                🎉 Upcoming Events: {s['upcoming_events']}
                ━━━━━━━━━━━━━━━━━━━━━━
                🔌 Powered by Aether MCP Server (port 8765)"""

                briefing_btn.click(fn=run_daily_briefing, outputs=briefing_output)

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

                gr.HTML("<hr style='border-color:#1e2a45;margin:16px 0;'>")
                export_btn = gr.Button("📄 Download Full Report (PDF)", variant="primary")
                export_status = gr.Textbox(label="Export Status", interactive=False, lines=3)
                export_btn.click(fn=generate_pdf_report, outputs=export_status)

            with gr.Tab("📊 Analytics"):
                gr.HTML("<p style='color:#94a3b8;margin-bottom:16px;'>Your real usage data visualized.</p>")
                refresh_btn = gr.Button("🔄 Refresh Charts", variant="primary")
                analytics_output = gr.HTML(label="Charts")

                def build_analytics():
                    if not os.path.isfile(ANALYTICS_FILE):
                        return "<p style='color:#94a3b8;'>No data yet. Use the agent first!</p>"
                    
                    # Read CSV
                    rows = []
                    with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            rows.append(row)
                    
                    if not rows:
                        return "<p style='color:#94a3b8;'>No data yet!</p>"

                    # Count domains
                    domains = {}
                    actions = {}
                    dates = {}
                    for row in rows:
                        d = row.get("Domain", "UNKNOWN")
                        a = row.get("Action", "UNKNOWN")
                        t = row.get("Timestamp", "")[:10]
                        domains[d] = domains.get(d, 0) + 1
                        actions[a] = actions.get(a, 0) + 1
                        dates[t] = dates.get(t, 0) + 1

                    # Domain colors
                    domain_colors = {
                        "TASKS": "#6366f1",
                        "HEALTH": "#34d399",
                        "EVENTS": "#c084fc",
                        "GARDEN": "#86efac",
                        "UNKNOWN": "#64748b"
                    }

                    # Build domain bars
                    max_domain = max(domains.values()) if domains else 1
                    domain_bars = ""
                    for d, count in sorted(domains.items(), key=lambda x: -x[1]):
                        color = domain_colors.get(d, "#6366f1")
                        width = int((count / max_domain) * 100)
                        domain_bars += f"""
                        <div style="margin-bottom:12px;">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="color:#e2e8f0;font-size:13px;font-weight:600;">{d}</span>
                                <span style="color:{color};font-size:13px;font-weight:700;">{count} actions</span>
                            </div>
                            <div style="background:#1e2a45;border-radius:6px;height:12px;">
                                <div style="background:{color};width:{width}%;height:12px;
                                    border-radius:6px;transition:width 0.3s;"></div>
                            </div>
                        </div>"""

                    # Build action bars (top 6)
                    max_action = max(actions.values()) if actions else 1
                    action_bars = ""
                    for a, count in sorted(actions.items(), key=lambda x: -x[1])[:6]:
                        width = int((count / max_action) * 100)
                        action_bars += f"""
                        <div style="margin-bottom:10px;">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="color:#94a3b8;font-size:12px;">{a}</span>
                                <span style="color:#6366f1;font-size:12px;font-weight:700;">{count}x</span>
                            </div>
                            <div style="background:#1e2a45;border-radius:4px;height:8px;">
                                <div style="background:linear-gradient(90deg,#6366f1,#8b5cf6);
                                    width:{width}%;height:8px;border-radius:4px;"></div>
                            </div>
                        </div>"""

                    # Build daily activity
                    daily_bars = ""
                    max_daily = max(dates.values()) if dates else 1
                    for day, count in sorted(dates.items())[-7:]:
                        height = max(20, int((count / max_daily) * 80))
                        daily_bars += f"""
                        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
                            <span style="color:#6366f1;font-size:11px;font-weight:700;">{count}</span>
                            <div style="background:linear-gradient(180deg,#6366f1,#8b5cf6);
                                width:32px;height:{height}px;border-radius:4px 4px 0 0;"></div>
                            <span style="color:#64748b;font-size:10px;">{day[5:]}</span>
                        </div>"""

                    total = len(rows)
                    html = f"""
                    <div style="background:#0a0e1a;padding:20px;border-radius:12px;">
                        
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:24px;">
                            <div style="background:#111827;border:1px solid #1e2a45;border-radius:10px;padding:16px;text-align:center;">
                                <div style="font-size:28px;font-weight:700;color:#6366f1;">{total}</div>
                                <div style="color:#64748b;font-size:12px;margin-top:4px;">Total Actions</div>
                            </div>
                            <div style="background:#111827;border:1px solid #1e2a45;border-radius:10px;padding:16px;text-align:center;">
                                <div style="font-size:28px;font-weight:700;color:#34d399;">{len(domains)}</div>
                                <div style="color:#64748b;font-size:12px;margin-top:4px;">Domains Used</div>
                            </div>
                            <div style="background:#111827;border:1px solid #1e2a45;border-radius:10px;padding:16px;text-align:center;">
                                <div style="font-size:28px;font-weight:700;color:#c084fc;">{len(dates)}</div>
                                <div style="color:#64748b;font-size:12px;margin-top:4px;">Active Days</div>
                            </div>
                        </div>

                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;">
                            <div style="background:#111827;border:1px solid #1e2a45;border-radius:10px;padding:16px;">
                                <h3 style="color:#e2e8f0;margin:0 0 16px;font-size:14px;">📊 Usage by Domain</h3>
                                {domain_bars}
                            </div>
                            <div style="background:#111827;border:1px solid #1e2a45;border-radius:10px;padding:16px;">
                                <h3 style="color:#e2e8f0;margin:0 0 16px;font-size:14px;">⚡ Top Actions</h3>
                                {action_bars}
                            </div>
                        </div>

                        <div style="background:#111827;border:1px solid #1e2a45;border-radius:10px;padding:16px;">
                            <h3 style="color:#e2e8f0;margin:0 0 16px;font-size:14px;">📅 Daily Activity (Last 7 Days)</h3>
                            <div style="display:flex;align-items:flex-end;gap:12px;height:120px;padding-bottom:8px;">
                                {daily_bars}
                            </div>
                        </div>

                    </div>"""
                    return html

                refresh_btn.click(fn=build_analytics, outputs=analytics_output)
                analytics_output.value = build_analytics()

            with gr.Tab("🛡️ Guardian"):
                gr.HTML("<p style='color:#94a3b8;margin-bottom:16px;'>Autonomous life monitor — runs in background, no input needed.</p>")
                
                with gr.Row():
                    guardian_refresh_btn = gr.Button("🔄 Check Guardian Status", variant="primary")
                    guardian_report_btn = gr.Button("📋 Full Caregiver Report", variant="secondary")
                
                guardian_output = gr.Textbox(
                    label="🛡️ Guardian Status",
                    lines=20,
                    interactive=False,
                    value="Click 'Check Guardian Status' to see live monitoring results."
                )

                def check_guardian():
                    risk = guardian_status["risk_level"]
                    alerts = guardian_status["alerts"]
                    last = guardian_status["last_check"] or "Checking..."
                    risk_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "🟢")
                    
                    status = f"""{risk_icon} GUARDIAN ACTIVE
    Last Check: {last}
    Risk Level: {risk}
    Active Alerts: {len(alerts)}

"""
                    if alerts:
                        status += "ALERTS:\n"
                        for a in alerts:
                            status += f"  ⚠️ {a}\n"
                    else:
                        status += "✅ All clear! No alerts detected."
                    
                    return status

                guardian_refresh_btn.click(fn=check_guardian, outputs=guardian_output)
                guardian_report_btn.click(fn=get_guardian_report, outputs=guardian_output)
                
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