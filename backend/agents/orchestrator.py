import re
import json
import logging
from datetime import datetime

from agents.context_agent import ContextAgent
from agents.task_agent import TaskAgent
from agents.schedule_agent import ScheduleAgent
from agents.notes_agent import NotesAgent
from agents.gmail_agent import GmailAgent
from agents.drive_agent import DriveAgent
from database.alloydb import create_workflow_log, complete_workflow_log
from tools.mcp_tools import MCP_TOOLS, list_tools, google_tools_available

logger = logging.getLogger(__name__)

# Gemini integration (optional - falls back to regex if not configured)
_gemini_available = False
try:
    from agents.gemini_engine import is_gemini_configured, parse_intent, generate_response, chat_response
    _gemini_available = is_gemini_configured()
    if _gemini_available:
        logger.info("Gemini NLU engine enabled")
    else:
        logger.info("Gemini API key not set - using regex intent parser")
except Exception as e:
    logger.warning(f"Gemini import failed: {e} - using regex intent parser")


class OrchestratorAgent:
    """
    Primary orchestrator using Gemini for NLU (with regex fallback).
    Coordinates 6 sub-agents and multiple MCP tools.
    """

    def __init__(self):
        self.name = "Nexus Orchestrator"
        self.sub_agents = {
            "context": ContextAgent(),
            "task": TaskAgent(),
            "schedule": ScheduleAgent(),
            "notes": NotesAgent(),
            "gmail": GmailAgent(),
            "drive": DriveAgent(),
        }
        self.mcp_tools = MCP_TOOLS
        self.gemini_enabled = _gemini_available

    def process_request(self, user_prompt: str, user_id: str) -> dict:
        """Parse user intent (Gemini or regex) and delegate to appropriate sub-agent."""
        try:
            # Parse intent
            if self.gemini_enabled:
                intent = parse_intent(user_prompt)
            else:
                intent = self._regex_parse_intent(user_prompt)

            agent_key = intent.get("agent")

            # Multi-step workflow
            if agent_key == "workflow":
                return self._execute_workflow(intent, user_id)

            # Help
            if agent_key == "help":
                return self._help_response()

            # General chat (Gemini-powered)
            if agent_key == "general":
                if self.gemini_enabled:
                    msg = chat_response(user_prompt)
                else:
                    msg = self._fallback_message(user_prompt)
                return {
                    "message": msg,
                    "actions": ["Handled by Orchestrator"],
                    "agent": self.name,
                }

            # Route to sub-agent
            if agent_key in self.sub_agents:
                agent = self.sub_agents[agent_key]
                result = agent.handle(intent, user_id)
                message = result["message"]

                # Optionally enhance response with Gemini
                if self.gemini_enabled:
                    enhanced = generate_response(
                        intent.get("action", ""), agent.name, result.get("data", {}), user_prompt
                    )
                    if enhanced:
                        message = enhanced

                return {
                    "message": message,
                    "actions": result["actions"],
                    "agent": result["agent"],
                }

            # No match
            return {
                "message": self._fallback_message(user_prompt),
                "actions": ["No specific intent matched"],
                "agent": self.name,
            }

        except Exception as e:
            logger.exception("Error processing request")
            return {
                "message": f"An error occurred: {str(e)}",
                "actions": [f"ERROR: {str(e)}"],
                "agent": "Error Handler",
            }

    # =============== Regex Fallback Parser ===============

    def _regex_parse_intent(self, prompt: str) -> dict:
        """Regex-based intent parsing (used when Gemini is not available)."""
        lower = prompt.lower().strip()

        # Help
        if lower in ("help", "what can you do", "what can you do?", "commands"):
            return {"agent": "help"}

        # Workflows
        if any(p in lower for p in ["plan my day", "daily plan", "morning routine"]):
            return {"agent": "workflow", "action": "plan_my_day"}
        if any(p in lower for p in ["weekly review", "week summary", "weekly summary"]):
            return {"agent": "workflow", "action": "weekly_review"}

        # Memory: retrieve
        if any(p in lower for p in [
            "what do you remember", "what did i say", "recall", "my memories",
            "show memory", "show memories", "retrieve memory",
        ]) or ("what" in lower and ("remember" in lower or "memory" in lower)):
            cat_match = re.search(r"(?:about|category|in)\s+(\w+)", lower)
            return {"agent": "context", "action": "retrieve_memory", "params": {"category": cat_match.group(1) if cat_match else None}}

        # Memory: store
        if lower.startswith("remember") or "remember that" in lower:
            content = re.sub(r"^remember\s+(?:that\s+)?", "", prompt, flags=re.IGNORECASE).strip()
            return {"agent": "context", "action": "store_memory", "params": {"content": content}}

        # Tasks: complete
        m = re.match(r"(?:complete|finish|done|close)\s+task\s*#?\s*(\d+)", lower)
        if m:
            return {"agent": "task", "action": "complete_task", "params": {"id": int(m.group(1))}}

        # Tasks: delete
        m = re.match(r"(?:delete|remove)\s+task\s*#?\s*(\d+)", lower)
        if m:
            return {"agent": "task", "action": "delete_task", "params": {"id": int(m.group(1))}}

        # Tasks: list
        if any(p in lower for p in ["show my tasks", "list tasks", "my tasks", "show tasks", "open tasks", "pending tasks", "all tasks"]):
            status = "open" if ("open" in lower or "pending" in lower) else ("done" if ("done" in lower or "completed" in lower) else None)
            return {"agent": "task", "action": "list_tasks", "params": {"status": status}}

        # Tasks: create
        if any(t in lower for t in ["create task", "add task", "new task", "task:"]):
            title = re.sub(r"^(?:create|add|new)\s+task[:\s]*", "", prompt, flags=re.IGNORECASE).strip() or prompt
            priority = "high" if ("high priority" in lower or "urgent" in lower) else ("low" if "low priority" in lower else "medium")
            title = re.sub(r"\s*(?:high priority|low priority|urgent|important)\s*", " ", title, flags=re.IGNORECASE).strip()
            due_match = re.search(r"(?:due|by|before)\s+(.+?)$", lower)
            due_date = due_match.group(1).strip() if due_match else None
            if due_date:
                title = re.sub(r"\s*(?:due|by|before)\s+.+$", "", title, flags=re.IGNORECASE).strip()
            return {"agent": "task", "action": "create_task", "params": {"title": title, "priority": priority, "due_date": due_date}}

        # Notes: delete
        m = re.match(r"(?:delete|remove)\s+note\s*#?\s*(\d+)", lower)
        if m:
            return {"agent": "notes", "action": "delete_note", "params": {"id": int(m.group(1))}}

        # Notes: list
        if any(p in lower for p in ["show my notes", "list notes", "my notes", "show notes", "all notes"]):
            tag_match = re.search(r"(?:tag|tagged|about)\s+(\w+)", lower)
            return {"agent": "notes", "action": "list_notes", "params": {"tag": tag_match.group(1) if tag_match else None}}

        # Notes: create
        if any(t in lower for t in ["note:", "create note", "add note", "new note", "take note", "write note"]):
            content = re.sub(r"^(?:create|add|new|take|write)\s+(?:a\s+)?note[:\s]*", "", prompt, flags=re.IGNORECASE).strip()
            if content.startswith("note:"):
                content = content[5:].strip()
            title_end = min(content.find(".") if content.find(".") > 0 else len(content), 50)
            title = content[:title_end].strip()
            tags_match = re.search(r"#(\w+)", content)
            return {"agent": "notes", "action": "create_note", "params": {"title": title, "content": content, "tags": tags_match.group(1) if tags_match else ""}}

        # Events: delete/cancel
        m = re.match(r"(?:delete|cancel|remove)\s+(?:event|meeting)\s*#?\s*(\d+)", lower)
        if m:
            return {"agent": "schedule", "action": "delete_event", "params": {"id": int(m.group(1))}}

        # Events: list
        if any(p in lower for p in ["show my calendar", "list events", "my events", "my calendar", "show events", "upcoming events", "show schedule", "my schedule"]):
            return {"agent": "schedule", "action": "list_events", "params": {}}

        # Events: create
        if any(t in lower for t in ["schedule", "meeting", "appointment", "event:"]):
            title = re.sub(r"^(?:schedule\s+(?:a\s+)?(?:meeting|appointment|event)?[:\s]*|book\s+(?:a\s+)?)", "", prompt, flags=re.IGNORECASE).strip() or "New Meeting"
            time_match = re.search(r"(?:at|from|on)\s+(.+?)(?:\s+(?:to|until|-)\s+(.+?))?(?:\s+(?:at|in)\s+(.+))?$", title, re.IGNORECASE)
            start_time, end_time, location = "TBD", None, ""
            if time_match:
                start_time = time_match.group(1).strip()
                end_time = time_match.group(2).strip() if time_match.group(2) else None
                location = time_match.group(3).strip() if time_match.group(3) else ""
                title = title[:time_match.start()].strip() or title
            return {"agent": "schedule", "action": "create_event", "params": {"title": title, "start_time": start_time, "end_time": end_time, "location": location}}

        # Gmail
        if any(p in lower for p in ["check my email", "read my email", "inbox", "read inbox", "show my email", "check email", "check gmail"]):
            return {"agent": "gmail", "action": "read_inbox", "params": {"max_results": 10}}
        if any(p in lower for p in ["search email", "find email", "search gmail"]):
            query = re.sub(r"^(?:search|find)\s+(?:emails?|gmail)\s+(?:about|for|regarding)?\s*", "", prompt, flags=re.IGNORECASE).strip()
            return {"agent": "gmail", "action": "search_emails", "params": {"query": query}}
        if any(p in lower for p in ["send email", "send mail", "email to", "mail to"]):
            return {"agent": "gmail", "action": "send_email", "params": {"raw": prompt}}

        # Drive
        if any(p in lower for p in ["search drive", "find file", "search files", "look for file"]):
            query = re.sub(r"^(?:search|find)\s+(?:drive|files?)\s+(?:for|about|named)?\s*", "", prompt, flags=re.IGNORECASE).strip()
            return {"agent": "drive", "action": "search_files", "params": {"query": query}}
        if any(p in lower for p in ["recent files", "show files", "my files", "list files", "show drive"]):
            return {"agent": "drive", "action": "list_recent", "params": {}}

        # Fuzzy task detection
        if "task" in lower:
            return {"agent": "task", "action": "create_task", "params": {"title": prompt.strip(), "priority": "medium"}}

        # General / no match
        return {"agent": "general", "action": "chat", "params": {}}

    # =============== Workflow Execution ===============

    def _execute_workflow(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action", "plan_my_day")

        if action == "plan_my_day":
            steps = [
                {"agent": "task", "action": "list_tasks", "params": {"status": "open"}},
                {"agent": "schedule", "action": "list_events", "params": {}},
                {"agent": "context", "action": "retrieve_memory", "params": {}},
            ]
            # Add Gmail if available
            if "gmail" in self.mcp_tools:
                steps.append({"agent": "gmail", "action": "read_inbox", "params": {"max_results": 5}})
            workflow_name = "Daily Planning"
        elif action == "weekly_review":
            steps = [
                {"agent": "task", "action": "list_tasks", "params": {}},
                {"agent": "schedule", "action": "list_events", "params": {}},
                {"agent": "notes", "action": "list_notes", "params": {}},
            ]
            workflow_name = "Weekly Review"
        else:
            steps = [{"agent": "task", "action": "list_tasks", "params": {}}]
            workflow_name = "Custom Workflow"

        log = create_workflow_log(user_id, workflow_name, json.dumps([s.get("action") for s in steps]))
        all_actions = [f"Workflow started: {workflow_name}"]
        combined_messages = []

        for i, step in enumerate(steps, 1):
            agent_key = step["agent"]
            agent = self.sub_agents.get(agent_key)
            if not agent:
                all_actions.append(f"Step {i}: Agent '{agent_key}' not found - skipped")
                continue

            result = agent.handle(step, user_id)
            all_actions.append(f"Step {i} ({agent.name} -> {step['action']}): completed")
            combined_messages.append(f"**Step {i} - {agent.name}:**\n{result['message']}")

        complete_workflow_log(log["id"], "completed", json.dumps(combined_messages))
        all_actions.append("Workflow completed successfully")

        final_message = "\n\n".join(combined_messages)

        # Optionally summarize with Gemini
        if self.gemini_enabled:
            try:
                summary = chat_response(
                    f"Summarize this daily planning output in a helpful, brief way:\n{final_message}"
                )
                if summary:
                    final_message = summary
            except Exception:
                pass

        return {
            "message": final_message,
            "actions": all_actions,
            "agent": self.name,
        }

    def _help_response(self) -> dict:
        tools = list_tools()
        tool_list = "\n".join(f"  - {t['name']}: {t['description']}" for t in tools)
        agents = "\n".join(f"  - {a.name}: {a.description}" for a in self.sub_agents.values())
        google_status = "Connected" if google_tools_available() else "Not configured (place credentials.json in backend/)"
        gemini_status = "Active" if self.gemini_enabled else "Not configured (set GEMINI_API_KEY in .env)"
        return {
            "message": (
                f"I'm the Nexus Orchestrator coordinating {len(self.sub_agents)} sub-agents and "
                f"{len(self.mcp_tools)} MCP tools.\n\n"
                f"**Sub-Agents:**\n{agents}\n\n"
                f"**MCP Tools:**\n{tool_list}\n\n"
                f"**Gemini NLU:** {gemini_status}\n"
                f"**Google Services:** {google_status}\n\n"
                f"**Commands:**\n"
                f"  - Tasks: 'create task ...', 'show my tasks', 'complete task #N'\n"
                f"  - Calendar: 'schedule meeting ...', 'show my calendar'\n"
                f"  - Memory: 'remember that ...', 'what do you remember?'\n"
                f"  - Notes: 'note: ...', 'show my notes'\n"
                f"  - Email: 'check my email', 'search emails about ...', 'send email to ...'\n"
                f"  - Drive: 'search drive for ...', 'show recent files'\n"
                f"  - Workflows: 'plan my day', 'weekly review'"
            ),
            "actions": ["Displayed help information"],
            "agent": self.name,
        }

    def _fallback_message(self, prompt: str) -> str:
        return (
            f"I'm your Nexus Orchestrator. I can help with:\n"
            f"- Tasks, Calendar, Memory, Notes\n"
            f"- Email (Gmail), File search (Drive)\n"
            f"- Workflows: 'plan my day', 'weekly review'\n\n"
            f"You said: '{prompt}'"
        )

    def get_agent_status(self) -> dict:
        return {
            "orchestrator": self.name,
            "sub_agents": [{"name": a.name, "description": a.description} for a in self.sub_agents.values()],
            "mcp_tools": list_tools(),
            "total_agents": len(self.sub_agents) + 1,
            "total_tools": len(self.mcp_tools),
            "gemini_enabled": self.gemini_enabled,
            "google_services": google_tools_available(),
        }
