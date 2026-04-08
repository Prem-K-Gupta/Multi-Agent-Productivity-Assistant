"""
Model Context Protocol (MCP) tool implementations.

Each tool provides a standardized interface for agents to interact with
services. Local tools use SQLite; Google tools use real Google APIs.
"""

import abc
import logging
from database.alloydb import (
    create_event, get_events, delete_event,
    create_task, get_tasks, update_task, delete_task,
    create_note, get_notes, update_note, delete_note,
)

logger = logging.getLogger(__name__)


class MCPTool(abc.ABC):
    """Abstract base class for MCP tool integrations."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass

    @abc.abstractmethod
    def execute(self, action: str, params: dict) -> dict:
        pass

    def _success(self, message: str, data: dict = None) -> dict:
        return {"status": "success", "tool": self.name, "message": message, "data": data or {}}

    def _error(self, message: str) -> dict:
        return {"status": "error", "tool": self.name, "message": message}


# --------------- Local (SQLite-backed) Tools ---------------

class CalendarMCPTool(MCPTool):
    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "Local calendar - schedule and manage events (SQLite-backed)."

    def execute(self, action: str, params: dict) -> dict:
        user_id = params.get("user_id", "default_user")
        if action == "create":
            result = create_event(user_id, params.get("title", "Untitled"), params.get("start_time", "TBD"),
                                  params.get("end_time"), params.get("description", ""), params.get("location", ""))
            return self._success(f"Event '{result['title']}' created.", data=result)
        elif action == "list":
            events = get_events(user_id)
            return self._success(f"{len(events)} event(s) found.", data={"events": events})
        elif action == "delete":
            eid = params.get("id")
            if not eid:
                return self._error("Missing event ID.")
            return self._success(f"Event #{eid} deleted.") if delete_event(eid) else self._error("Event not found.")
        return self._error(f"Unknown action: {action}")


class TaskManagerMCPTool(MCPTool):
    @property
    def name(self) -> str:
        return "task_manager"

    @property
    def description(self) -> str:
        return "Local task manager - create, list, update tasks (SQLite-backed)."

    def execute(self, action: str, params: dict) -> dict:
        user_id = params.get("user_id", "default_user")
        if action == "create":
            result = create_task(user_id, params.get("title", "Untitled"), params.get("description", ""),
                                 params.get("priority", "medium"), params.get("due_date"))
            return self._success(f"Task '{result['title']}' created.", data=result)
        elif action == "list":
            tasks = get_tasks(user_id, status=params.get("status"))
            return self._success(f"{len(tasks)} task(s) found.", data={"tasks": tasks})
        elif action == "update":
            tid = params.get("id")
            if not tid:
                return self._error("Missing task ID.")
            result = update_task(tid, **{k: v for k, v in params.items() if k not in ("id", "user_id")})
            return self._success(f"Task #{tid} updated.", data=result) if "error" not in result else self._error(result["error"])
        elif action == "delete":
            tid = params.get("id")
            if not tid:
                return self._error("Missing task ID.")
            return self._success(f"Task #{tid} deleted.") if delete_task(tid) else self._error("Task not found.")
        return self._error(f"Unknown action: {action}")


class NotesMCPTool(MCPTool):
    @property
    def name(self) -> str:
        return "notes"

    @property
    def description(self) -> str:
        return "Local notes - create, list, update notes (SQLite-backed)."

    def execute(self, action: str, params: dict) -> dict:
        user_id = params.get("user_id", "default_user")
        if action == "create":
            result = create_note(user_id, params.get("title", "Untitled"), params.get("content", ""), params.get("tags", ""))
            return self._success(f"Note '{result['title']}' created.", data=result)
        elif action == "list":
            notes = get_notes(user_id, tag=params.get("tag"))
            return self._success(f"{len(notes)} note(s) found.", data={"notes": notes})
        elif action == "update":
            nid = params.get("id")
            if not nid:
                return self._error("Missing note ID.")
            result = update_note(nid, **{k: v for k, v in params.items() if k not in ("id", "user_id")})
            return self._success(f"Note #{nid} updated.", data=result) if "error" not in result else self._error(result["error"])
        elif action == "delete":
            nid = params.get("id")
            if not nid:
                return self._error("Missing note ID.")
            return self._success(f"Note #{nid} deleted.") if delete_note(nid) else self._error("Note not found.")
        return self._error(f"Unknown action: {action}")


# --------------- Tool Registry ---------------

# Always available: local tools
MCP_TOOLS = {
    "calendar": CalendarMCPTool(),
    "task_manager": TaskManagerMCPTool(),
    "notes": NotesMCPTool(),
}

# Always register Google tools — they handle per-user auth internally
# (each tool checks the user's token in the database at execute time)
try:
    from tools.google_calendar import GoogleCalendarTool
    from tools.google_tasks import GoogleTasksTool
    from tools.gmail_tool import GmailTool
    from tools.google_drive import GoogleDriveTool

    MCP_TOOLS["google_calendar"] = GoogleCalendarTool()
    MCP_TOOLS["google_tasks"] = GoogleTasksTool()
    MCP_TOOLS["gmail"] = GmailTool()
    MCP_TOOLS["google_drive"] = GoogleDriveTool()
    logger.info("Google MCP tools registered (per-user auth at execute time)")
except Exception as e:
    logger.warning(f"Failed to register Google tools: {e}")


def get_tool(name: str) -> MCPTool:
    return MCP_TOOLS.get(name)


def list_tools() -> list:
    return [{"name": t.name, "description": t.description} for t in MCP_TOOLS.values()]


def check_mcp_health() -> bool:
    try:
        for tool in MCP_TOOLS.values():
            assert hasattr(tool, "execute")
        return True
    except Exception:
        return False


def google_tools_available() -> bool:
    """Check if Google tools are registered."""
    return any(name.startswith("google") or name == "gmail" for name in MCP_TOOLS)


def google_authenticated_for_user(user_id: str = "default_user") -> bool:
    """Check if a specific user has connected their Google account."""
    try:
        from database.alloydb import get_google_token
        return get_google_token(user_id) is not None
    except Exception:
        return False
