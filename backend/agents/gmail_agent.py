from agents.base_agent import BaseAgent
from tools.mcp_tools import get_tool


class GmailAgent(BaseAgent):
    """Sub-agent for email management via Gmail."""

    def __init__(self):
        super().__init__(
            name="Gmail Agent",
            description="Reads inbox, searches emails, and sends messages via Gmail.",
        )

    def handle(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action")
        params = intent.get("params", {})
        params["user_id"] = user_id
        tool = get_tool("gmail")

        if not tool:
            return self._result(
                "Gmail is not configured. Place Google OAuth credentials.json in the backend/ folder and authenticate.",
                ["Gmail Agent: tool not available"],
            )

        if action == "read_inbox":
            result = tool.execute("read_inbox", params)
        elif action == "search_emails":
            result = tool.execute("search", params)
        elif action == "send_email":
            result = tool.execute("send", params)
        else:
            return self._result(
                "I can read your inbox, search emails, or send messages. Try 'check my email' or 'search emails about ...'.",
                ["Gmail Agent: awaiting valid action"],
            )

        if result["status"] == "error":
            return self._result(f"Gmail error: {result['message']}", ["Gmail Agent: error"])

        # Format response
        data = result.get("data", {})
        if action == "read_inbox" or action == "search_emails":
            emails = data.get("emails", [])
            if not emails:
                return self._result("No emails found.", ["Routed to Gmail Agent", "Queried Gmail API", "0 results"])
            lines = []
            for e in emails:
                lines.append(f"- **{e['subject']}** from {e['from']}\n  {e['snippet'][:80]}...")
            return self._result(
                f"Found {len(emails)} email(s):\n" + "\n".join(lines),
                ["Routed to Gmail Agent", "Invoked MCP Gmail tool", f"{len(emails)} results"],
                data=data,
            )
        elif action == "send_email":
            return self._result(
                f"Email sent to {data.get('to', 'recipient')} - Subject: {data.get('subject', '')}",
                ["Routed to Gmail Agent", "Invoked MCP Gmail tool", "Email sent"],
                data=data,
            )

        return self._result(result["message"], ["Routed to Gmail Agent"])
