from agents.base_agent import BaseAgent
from tools.mcp_tools import get_tool


class DriveAgent(BaseAgent):
    """Sub-agent for file management via Google Drive."""

    def __init__(self):
        super().__init__(
            name="Drive Agent",
            description="Searches and lists files from Google Drive.",
        )

    def handle(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action")
        params = intent.get("params", {})
        params["user_id"] = user_id
        tool = get_tool("google_drive")

        if not tool:
            return self._result(
                "Google Drive is not configured. Place Google OAuth credentials.json in the backend/ folder and authenticate.",
                ["Drive Agent: tool not available"],
            )

        if action == "search_files":
            result = tool.execute("search", params)
        elif action == "list_recent":
            result = tool.execute("list_recent", params)
        else:
            return self._result(
                "I can search or list files from Google Drive. Try 'search drive for ...' or 'show recent files'.",
                ["Drive Agent: awaiting valid action"],
            )

        if result["status"] == "error":
            return self._result(f"Drive error: {result['message']}", ["Drive Agent: error"])

        data = result.get("data", {})
        files = data.get("files", [])
        if not files:
            return self._result("No files found.", ["Routed to Drive Agent", "Queried Google Drive API", "0 results"])

        lines = []
        for f in files:
            link = f" - [link]({f['link']})" if f.get("link") else ""
            lines.append(f"- {f['name']} ({f.get('modified', '')}){link}")

        return self._result(
            f"Found {len(files)} file(s):\n" + "\n".join(lines),
            ["Routed to Drive Agent", "Invoked MCP Google Drive tool", f"{len(files)} results"],
            data=data,
        )
