from agents.base_agent import BaseAgent
from database.alloydb import create_task, get_tasks, update_task, delete_task


class TaskAgent(BaseAgent):
    """Sub-agent for task planning and management."""

    def __init__(self):
        super().__init__(
            name="Task Planning Agent",
            description="Creates, lists, updates, and manages tasks in the database.",
        )

    def handle(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action")
        params = intent.get("params", {})

        if action == "create_task":
            return self._create(user_id, params)
        elif action == "list_tasks":
            return self._list(user_id, params)
        elif action == "update_task":
            return self._update(params)
        elif action == "complete_task":
            return self._complete(params)
        elif action == "delete_task":
            return self._delete(params)
        else:
            return self._result(
                "I can create, list, update, or complete tasks. Try 'create task: ...' or 'show my tasks'.",
                ["Task Agent: awaiting valid action"],
            )

    def _create(self, user_id: str, params: dict) -> dict:
        title = params.get("title", "")
        if not title:
            return self._result("Please provide a task title.", ["Task Agent: missing title"])
        result = create_task(
            user_id,
            title,
            description=params.get("description", ""),
            priority=params.get("priority", "medium"),
            due_date=params.get("due_date"),
        )
        return self._result(
            f"Task created: '{title}' (priority: {result['priority']}, status: {result['status']})",
            [
                "Routed to Task Planning Agent",
                "Invoked MCP TaskManager tool",
                f"Executed INSERT on AlloyDB tasks table - Task #{result['id']}",
            ],
            data=result,
        )

    def _list(self, user_id: str, params: dict) -> dict:
        status_filter = params.get("status")
        tasks = get_tasks(user_id, status_filter)
        if not tasks:
            msg = "No tasks found."
            if status_filter:
                msg += f" (filter: status={status_filter})"
            return self._result(msg, ["Routed to Task Planning Agent", "Executed SELECT on AlloyDB tasks table", "0 results"])
        lines = []
        for t in tasks:
            priority_marker = {"high": "!!!", "medium": "!!", "low": "!"}.get(t["priority"], "!!")
            lines.append(f"- [{t['status'].upper()}] {priority_marker} #{t['id']}: {t['title']}")
        return self._result(
            f"Found {len(tasks)} task(s):\n" + "\n".join(lines),
            [
                "Routed to Task Planning Agent",
                "Executed SELECT on AlloyDB tasks table",
                f"{len(tasks)} results returned",
            ],
            data={"tasks": tasks},
        )

    def _update(self, params: dict) -> dict:
        task_id = params.get("id")
        if not task_id:
            return self._result("Please specify which task to update (by ID).", ["Task Agent: missing ID"])
        result = update_task(task_id, **{k: v for k, v in params.items() if k != "id"})
        if "error" in result:
            return self._result(result["error"], ["Task Agent: update failed"])
        return self._result(
            f"Task #{task_id} updated.",
            ["Routed to Task Planning Agent", f"Executed UPDATE on AlloyDB tasks table - Task #{task_id}"],
            data=result,
        )

    def _complete(self, params: dict) -> dict:
        task_id = params.get("id")
        if not task_id:
            return self._result("Please specify which task to complete (by ID).", ["Task Agent: missing ID"])
        result = update_task(task_id, status="done")
        if "error" in result:
            return self._result(result["error"], ["Task Agent: complete failed"])
        return self._result(
            f"Task #{task_id} marked as done!",
            ["Routed to Task Planning Agent", f"Executed UPDATE on AlloyDB tasks - status=done for Task #{task_id}"],
            data=result,
        )

    def _delete(self, params: dict) -> dict:
        task_id = params.get("id")
        if not task_id:
            return self._result("Please specify which task to delete (by ID).", ["Task Agent: missing ID"])
        success = delete_task(task_id)
        if success:
            return self._result(
                f"Task #{task_id} deleted.",
                ["Routed to Task Planning Agent", f"Deleted Task #{task_id} from AlloyDB"],
            )
        return self._result(f"Task #{task_id} not found.", ["Task Agent: ID not found"])
