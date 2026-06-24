import json
import os
from datetime import datetime, date, timedelta

# ==========================================
# AETHER CONCIERGE - MCP SERVER
# Provides 5 tools for external agent access
# ==========================================

SANDBOX_PATH = os.path.join(os.getcwd(), "Test_Desktop")
TASKS_FILE = os.path.join(SANDBOX_PATH, "daily_tasks.json")
HEALTH_FILE = os.path.join(SANDBOX_PATH, "health_tracker.json")
EVENTS_FILE = os.path.join(SANDBOX_PATH, "events.json")

# ==========================================
# HELPERS
# ==========================================
def load_json(filepath, default):
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

# ==========================================
# MCP TOOL 1: get_current_datetime
# ==========================================
def get_current_datetime() -> dict:
    """
    MCP Tool: Returns current date, time, day of week.
    Used by agent for smart scheduling and reminders.
    """
    now = datetime.now()
    return {
        "tool": "get_current_datetime",
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "full": now.strftime("%A, %B %d, %Y at %I:%M %p"),
        "timestamp": now.isoformat()
    }

# ==========================================
# MCP TOOL 2: check_overdue_tasks
# ==========================================
def check_overdue_tasks() -> dict:
    """
    MCP Tool: Finds all tasks that are past their due date.
    Enables proactive agent behavior — alerts user to overdue work.
    """
    data = load_json(TASKS_FILE, {"tasks": []})
    tasks = data.get("tasks", [])
    today = date.today()
    overdue = []

    for t in tasks:
        if t.get("status") != "pending":
            continue
        due = t.get("due_date", "")
        if not due:
            continue
        try:
            due_date = datetime.strptime(due[:10], "%Y-%m-%d").date()
            if due_date < today:
                days_overdue = (today - due_date).days
                overdue.append({
                    "title": t["title"],
                    "priority": t.get("priority", "medium"),
                    "due_date": due,
                    "days_overdue": days_overdue
                })
        except:
            continue

    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)

    return {
        "tool": "check_overdue_tasks",
        "count": len(overdue),
        "overdue_tasks": overdue,
        "message": f"{len(overdue)} overdue tasks found" if overdue else "No overdue tasks!"
    }

# ==========================================
# MCP TOOL 3: get_medication_due_today
# ==========================================
def get_medication_due_today() -> dict:
    """
    MCP Tool: Returns medications scheduled for today.
    Helps agent remind user about daily health routines.
    """
    health = load_json(HEALTH_FILE, {"medications": []})
    meds = health.get("medications", [])
    today_keywords = ["morning", "evening", "night", "daily",
                      "everyday", "noon", "afternoon", "bedtime"]
    due_today = []

    for m in meds:
        time_val = m.get("time", "").lower()
        # Include meds with daily/recurring times
        if any(k in time_val for k in today_keywords):
            due_today.append({
                "name": m["name"],
                "dose": m["dose"],
                "time": m["time"],
                "notes": m.get("notes", "")
            })
        # Include meds with no specific time (take daily)
        elif time_val in ["not specified", "", "none"]:
            due_today.append({
                "name": m["name"],
                "dose": m["dose"],
                "time": "No specific time",
                "notes": m.get("notes", "")
            })

    return {
        "tool": "get_medication_due_today",
        "date": date.today().strftime("%B %d, %Y"),
        "count": len(due_today),
        "medications": due_today,
        "message": f"{len(due_today)} medication(s) due today" if due_today
                   else "No medications scheduled for today"
    }

# ==========================================
# MCP TOOL 4: get_upcoming_events
# ==========================================
def get_upcoming_events(days_ahead: int = 7) -> dict:
    """
    MCP Tool: Returns events happening in the next N days.
    Gives agent calendar awareness for smart suggestions.
    """
    events_data = load_json(EVENTS_FILE, {"events": []})
    events = events_data.get("events", [])
    today = date.today()
    upcoming = []

    for e in events:
        event_date_str = e.get("date", "")
        try:
            for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    event_date = datetime.strptime(
                        event_date_str[:12].strip(), fmt
                    ).date()
                    break
                except:
                    continue
            else:
                continue

            days_until = (event_date - today).days
            if 0 <= days_until <= days_ahead:
                upcoming.append({
                    "title": e["title"],
                    "date": event_date_str,
                    "days_until": days_until,
                    "guests": len(e.get("guests", [])),
                    "notes": e.get("notes", "")
                })
        except:
            continue

    upcoming.sort(key=lambda x: x["days_until"])

    return {
        "tool": "get_upcoming_events",
        "days_ahead": days_ahead,
        "count": len(upcoming),
        "events": upcoming,
        "message": f"{len(upcoming)} event(s) in next {days_ahead} days"
    }

# ==========================================
# MCP TOOL 5: generate_daily_briefing
# ==========================================
def generate_daily_briefing() -> dict:
    """
    MCP Tool: Generates a complete morning briefing.
    The flagship tool — combines all data sources into
    one intelligent daily summary. True concierge behavior.
    """
    dt = get_current_datetime()
    overdue = check_overdue_tasks()
    meds = get_medication_due_today()
    events = get_upcoming_events(days_ahead=7)

    # Get today's pending tasks
    data = load_json(TASKS_FILE, {"tasks": []})
    all_tasks = data.get("tasks", [])
    pending = [t for t in all_tasks if t.get("status") == "pending"]
    high_priority = [t for t in pending if t.get("priority") == "high"]

    # Build briefing message
    briefing_parts = []
    briefing_parts.append(
        f"Good morning! Today is {dt['full']}."
    )

    if high_priority:
        briefing_parts.append(
            f"You have {len(high_priority)} HIGH priority task(s) "
            f"that need attention today."
        )

    if overdue["count"] > 0:
        briefing_parts.append(
            f"WARNING: {overdue['count']} task(s) are overdue!"
        )

    if meds["count"] > 0:
        med_names = ", ".join(m["name"] for m in meds["medications"])
        briefing_parts.append(
            f"Remember your medications today: {med_names}."
        )

    if events["count"] > 0:
        next_event = events["events"][0]
        if next_event["days_until"] == 0:
            briefing_parts.append(
                f"You have an event TODAY: {next_event['title']}!"
            )
        else:
            briefing_parts.append(
                f"Upcoming: {next_event['title']} "
                f"in {next_event['days_until']} day(s)."
            )

    if not any([high_priority, overdue["count"],
                meds["count"], events["count"]]):
        briefing_parts.append(
            "You're all clear today! Great time to add new goals."
        )

    return {
        "tool": "generate_daily_briefing",
        "datetime": dt["full"],
        "briefing": " ".join(briefing_parts),
        "summary": {
            "pending_tasks": len(pending),
            "high_priority": len(high_priority),
            "overdue": overdue["count"],
            "medications_today": meds["count"],
            "upcoming_events": events["count"]
        },
        "details": {
            "overdue_tasks": overdue["overdue_tasks"],
            "medications": meds["medications"],
            "events": events["events"]
        }
    }

# ==========================================
# MCP SERVER RUNNER
# ==========================================
# ==========================================
# TRUE MCP HTTP SERVER
# Runs as separate process on port 8765
# Any agent can connect to this server
# ==========================================
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

class MCPHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Clean logging
        print(f"[MCP] {args[0]} {args[1]}")

    def send_json(self, data: dict, status: int = 200):
        response = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # ── Tool routing ──
        if path == "/":
            self.send_json({
                "server": "Aether Concierge MCP Server",
                "version": "1.0.0",
                "tools": [
                    "get_current_datetime",
                    "check_overdue_tasks",
                    "get_medication_due_today",
                    "get_upcoming_events",
                    "generate_daily_briefing"
                ]
            })

        elif path == "/get_current_datetime":
            self.send_json(get_current_datetime())

        elif path == "/check_overdue_tasks":
            self.send_json(check_overdue_tasks())

        elif path == "/get_medication_due_today":
            self.send_json(get_medication_due_today())

        elif path == "/get_upcoming_events":
            # Optional query param: ?days=7
            params = urllib.parse.parse_qs(parsed.query)
            days = int(params.get("days", [7])[0])
            self.send_json(get_upcoming_events(days_ahead=days))

        elif path == "/generate_daily_briefing":
            self.send_json(generate_daily_briefing())

        else:
            self.send_json({
                "error": f"Tool '{path}' not found",
                "available_tools": [
                    "/get_current_datetime",
                    "/check_overdue_tasks", 
                    "/get_medication_due_today",
                    "/get_upcoming_events",
                    "/generate_daily_briefing"
                ]
            }, status=404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()


def run_mcp_server(port: int = 8765):
    server = HTTPServer(("127.0.0.1", port), MCPHandler)
    print(f"[MCP Server] Running on http://127.0.0.1:{port}")
    print(f"[MCP Server] Available tools:")
    print(f"  GET http://127.0.0.1:{port}/get_current_datetime")
    print(f"  GET http://127.0.0.1:{port}/check_overdue_tasks")
    print(f"  GET http://127.0.0.1:{port}/get_medication_due_today")
    print(f"  GET http://127.0.0.1:{port}/get_upcoming_events")
    print(f"  GET http://127.0.0.1:{port}/generate_daily_briefing")
    server.serve_forever()


if __name__ == "__main__":
    run_mcp_server()