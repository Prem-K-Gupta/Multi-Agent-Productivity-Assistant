from agents.base_agent import BaseAgent
from database.alloydb import create_event, get_events, delete_event


class ScheduleAgent(BaseAgent):
    """Sub-agent for calendar scheduling and event management."""

    def __init__(self):
        super().__init__(
            name="Scheduling Agent",
            description="Schedules meetings, manages calendar events via MCP Calendar tool.",
        )

    def handle(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action")
        params = intent.get("params", {})

        if action == "create_event":
            return self._create(user_id, params)
        elif action == "list_events":
            return self._list(user_id)
        elif action == "delete_event":
            return self._delete(params)
        else:
            return self._result(
                "I can schedule meetings and manage calendar events. Try 'schedule a meeting ...' or 'show my calendar'.",
                ["Schedule Agent: awaiting valid action"],
            )

    def _create(self, user_id: str, params: dict) -> dict:
        title = params.get("title", "New Meeting")
        start_time = params.get("start_time", "TBD")
        end_time = params.get("end_time")
        description = params.get("description", "")
        location = params.get("location", "")

        result = create_event(user_id, title, start_time, end_time, description, location)
        parts = [f"Event scheduled: '{title}' at {start_time}"]
        if end_time:
            parts.append(f"until {end_time}")
        if location:
            parts.append(f"at {location}")

        return self._result(
            " ".join(parts),
            [
                "Routed to Scheduling Agent",
                "Invoked MCP Calendar tool",
                f"Executed INSERT on AlloyDB events table - Event #{result['id']}",
            ],
            data=result,
        )

    def _list(self, user_id: str) -> dict:
        events = get_events(user_id)
        if not events:
            return self._result(
                "No events on your calendar.",
                ["Routed to Scheduling Agent", "Executed SELECT on AlloyDB events table", "0 results"],
            )
        lines = []
        for e in events:
            time_str = e["start_time"]
            if e.get("end_time"):
                time_str += f" - {e['end_time']}"
            loc = f" @ {e['location']}" if e.get("location") else ""
            lines.append(f"- #{e['id']}: {e['title']} ({time_str}){loc}")
        return self._result(
            f"Found {len(events)} event(s):\n" + "\n".join(lines),
            [
                "Routed to Scheduling Agent",
                "Invoked MCP Calendar tool",
                f"{len(events)} results returned",
            ],
            data={"events": events},
        )

    def _delete(self, params: dict) -> dict:
        event_id = params.get("id")
        if not event_id:
            return self._result("Please specify which event to cancel (by ID).", ["Schedule Agent: missing ID"])
        success = delete_event(event_id)
        if success:
            return self._result(
                f"Event #{event_id} cancelled.",
                ["Routed to Scheduling Agent", f"Deleted Event #{event_id} from AlloyDB"],
            )
        return self._result(f"Event #{event_id} not found.", ["Schedule Agent: ID not found"])
