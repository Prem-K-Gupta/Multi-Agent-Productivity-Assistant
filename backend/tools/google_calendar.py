"""
Google Calendar MCP Tool - Real integration with Google Calendar API.
"""

import logging
from datetime import datetime, timedelta
from tools.mcp_tools import MCPTool
from google_auth import get_service_for_user
from database.alloydb import get_google_token

logger = logging.getLogger(__name__)


class GoogleCalendarTool(MCPTool):
    """MCP tool for Google Calendar - create, list, and delete real calendar events."""

    @property
    def name(self) -> str:
        return "google_calendar"

    @property
    def description(self) -> str:
        return "Google Calendar - create, list, and manage real calendar events."

    def _get_service(self, token_json: str):
        return get_service_for_user("calendar", "v3", token_json)

    def execute(self, action: str, params: dict) -> dict:
        user_id = params.get("user_id", "default_user")
        token_row = get_google_token(user_id)
        if not token_row:
            return self._error("Google not authenticated. Sign in via the Google login button first.")

        token_json = token_row["token_json"]

        try:
            if action == "create":
                return self._create_event(token_json, params)
            elif action == "list":
                return self._list_events(token_json, params)
            elif action == "delete":
                return self._delete_event(token_json, params)
            else:
                return self._error(f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Google Calendar error")
            return self._error(str(e))

    def _create_event(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        title = params.get("title", "Untitled Event")
        start_time = params.get("start_time", "")
        end_time = params.get("end_time", "")
        location = params.get("location", "")
        description = params.get("description", "")

        start_dt, end_dt = self._parse_times(start_time, end_time)

        event_body = {
            "summary": title,
            "location": location,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }

        event = service.events().insert(calendarId="primary", body=event_body).execute()
        return self._success(
            f"Event '{title}' created on Google Calendar.",
            data={
                "id": event["id"],
                "title": event["summary"],
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "link": event.get("htmlLink", ""),
            },
        )

    def _list_events(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        max_results = params.get("max_results", 10)

        now = datetime.utcnow().isoformat() + "Z"
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = result.get("items", [])
        event_list = []
        for e in events:
            event_list.append({
                "id": e["id"],
                "title": e.get("summary", "No Title"),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location", ""),
            })
        return self._success(f"{len(event_list)} upcoming event(s) from Google Calendar.", data={"events": event_list})

    def _delete_event(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        event_id = params.get("id")
        if not event_id:
            return self._error("Missing event ID.")
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return self._success(f"Event '{event_id}' deleted from Google Calendar.")

    def _parse_times(self, start_str: str, end_str: str):
        """Best-effort parsing of time strings into datetime objects."""
        now = datetime.utcnow()

        start_dt = self._try_parse(start_str, now)
        if start_dt is None:
            start_dt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        if end_str:
            end_dt = self._try_parse(end_str, now)
            if end_dt is None:
                end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = start_dt + timedelta(hours=1)

        return start_dt, end_dt

    def _try_parse(self, time_str: str, reference: datetime):
        """Try multiple datetime formats."""
        if not time_str or time_str == "TBD":
            return None
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %I:%M%p",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
            "%B %d, %Y %H:%M",
            "%B %d %H:%M",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue

        import re
        time_match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_str.strip(), re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm and ampm.lower() == "pm" and hour < 12:
                hour += 12
            elif ampm and ampm.lower() == "am" and hour == 12:
                hour = 0
            return reference.replace(hour=hour, minute=minute, second=0, microsecond=0)

        return None
