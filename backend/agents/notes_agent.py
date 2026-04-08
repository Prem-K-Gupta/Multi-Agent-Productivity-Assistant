from agents.base_agent import BaseAgent
from database.alloydb import create_note, get_notes, update_note, delete_note


class NotesAgent(BaseAgent):
    """Sub-agent for managing notes and information."""

    def __init__(self):
        super().__init__(
            name="Notes Agent",
            description="Creates, retrieves, updates, and deletes notes for information management.",
        )

    def handle(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action")
        params = intent.get("params", {})

        if action == "create_note":
            return self._create(user_id, params)
        elif action == "list_notes":
            return self._list(user_id, params)
        elif action == "update_note":
            return self._update(params)
        elif action == "delete_note":
            return self._delete(params)
        else:
            return self._result(
                "I can create and manage notes. Try 'note: ...' or 'show my notes'.",
                ["Notes Agent: awaiting valid action"],
            )

    def _create(self, user_id: str, params: dict) -> dict:
        title = params.get("title", "")
        if not title:
            return self._result("Please provide a note title.", ["Notes Agent: missing title"])
        result = create_note(
            user_id,
            title,
            content=params.get("content", ""),
            tags=params.get("tags", ""),
        )
        return self._result(
            f"Note created: '{title}'",
            [
                "Routed to Notes Agent",
                f"Executed INSERT on AlloyDB notes table - Note #{result['id']}",
            ],
            data=result,
        )

    def _list(self, user_id: str, params: dict) -> dict:
        tag = params.get("tag")
        notes = get_notes(user_id, tag)
        if not notes:
            return self._result(
                "No notes found." + (f" (tag: {tag})" if tag else ""),
                ["Routed to Notes Agent", "Executed SELECT on AlloyDB notes table", "0 results"],
            )
        lines = []
        for n in notes:
            tag_str = f" [{n['tags']}]" if n.get("tags") else ""
            lines.append(f"- #{n['id']}: {n['title']}{tag_str}")
        return self._result(
            f"Found {len(notes)} note(s):\n" + "\n".join(lines),
            ["Routed to Notes Agent", f"{len(notes)} results returned"],
            data={"notes": notes},
        )

    def _update(self, params: dict) -> dict:
        note_id = params.get("id")
        if not note_id:
            return self._result("Please specify which note to update (by ID).", ["Notes Agent: missing ID"])
        result = update_note(note_id, **{k: v for k, v in params.items() if k != "id"})
        if "error" in result:
            return self._result(result["error"], ["Notes Agent: update failed"])
        return self._result(
            f"Note #{note_id} updated.",
            ["Routed to Notes Agent", f"Executed UPDATE on AlloyDB notes table - Note #{note_id}"],
            data=result,
        )

    def _delete(self, params: dict) -> dict:
        note_id = params.get("id")
        if not note_id:
            return self._result("Please specify which note to delete (by ID).", ["Notes Agent: missing ID"])
        success = delete_note(note_id)
        if success:
            return self._result(
                f"Note #{note_id} deleted.",
                ["Routed to Notes Agent", f"Deleted Note #{note_id} from AlloyDB"],
            )
        return self._result(f"Note #{note_id} not found.", ["Notes Agent: ID not found"])
