"""
Google Tasks MCP Tool - Real integration with Google Tasks API.
"""

import logging
from tools.mcp_tools import MCPTool
from google_auth import get_service_for_user
from database.alloydb import get_google_token

logger = logging.getLogger(__name__)


class GoogleTasksTool(MCPTool):
    """MCP tool for Google Tasks - create, list, complete, and delete real tasks."""

    @property
    def name(self) -> str:
        return "google_tasks"

    @property
    def description(self) -> str:
        return "Google Tasks - create, list, complete, and manage real tasks."

    def _get_service(self, token_json: str):
        return get_service_for_user("tasks", "v1", token_json)

    def _get_tasklist_id(self, token_json: str):
        """Get the default task list ID."""
        service = self._get_service(token_json)
        results = service.tasklists().list(maxResults=1).execute()
        items = results.get("items", [])
        if items:
            return items[0]["id"]
        return "@default"

    def execute(self, action: str, params: dict) -> dict:
        user_id = params.get("user_id", "default_user")
        token_row = get_google_token(user_id)
        if not token_row:
            return self._error("Google not authenticated. Sign in via the Google login button first.")

        token_json = token_row["token_json"]

        try:
            if action == "create":
                return self._create_task(token_json, params)
            elif action == "list":
                return self._list_tasks(token_json, params)
            elif action == "complete":
                return self._complete_task(token_json, params)
            elif action == "delete":
                return self._delete_task(token_json, params)
            else:
                return self._error(f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Google Tasks error")
            return self._error(str(e))

    def _create_task(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        tasklist_id = self._get_tasklist_id(token_json)

        title = params.get("title", "Untitled Task")
        notes = params.get("description", "")
        due = params.get("due_date", "")

        task_body = {"title": title, "notes": notes}
        if due:
            if "T" not in due:
                due += "T00:00:00.000Z"
            task_body["due"] = due

        task = service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
        return self._success(
            f"Task '{title}' created in Google Tasks.",
            data={
                "id": task["id"],
                "title": task["title"],
                "status": task["status"],
                "due": task.get("due", ""),
            },
        )

    def _list_tasks(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        tasklist_id = self._get_tasklist_id(token_json)
        max_results = params.get("max_results", 20)
        show_completed = params.get("show_completed", False)

        result = service.tasks().list(
            tasklist=tasklist_id,
            maxResults=max_results,
            showCompleted=show_completed,
        ).execute()

        tasks = result.get("items", [])
        task_list = []
        for t in tasks:
            task_list.append({
                "id": t["id"],
                "title": t.get("title", "No Title"),
                "status": t.get("status", "needsAction"),
                "due": t.get("due", ""),
                "notes": t.get("notes", ""),
            })
        return self._success(f"{len(task_list)} task(s) from Google Tasks.", data={"tasks": task_list})

    def _complete_task(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        tasklist_id = self._get_tasklist_id(token_json)
        task_id = params.get("id")
        if not task_id:
            return self._error("Missing task ID.")

        task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        task["status"] = "completed"
        updated = service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
        return self._success(f"Task '{updated.get('title', '')}' marked as completed.", data={"id": task_id, "status": "completed"})

    def _delete_task(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        tasklist_id = self._get_tasklist_id(token_json)
        task_id = params.get("id")
        if not task_id:
            return self._error("Missing task ID.")

        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return self._success(f"Task '{task_id}' deleted from Google Tasks.")
