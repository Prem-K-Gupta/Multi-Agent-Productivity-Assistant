from agents.base_agent import BaseAgent
from database.alloydb import save_to_memory, get_memory, delete_memory


class ContextAgent(BaseAgent):
    """Sub-agent for memory/context retrieval and storage."""

    def __init__(self):
        super().__init__(
            name="Context Retrieval Agent",
            description="Manages long-term memory storage and retrieval from the database.",
        )

    def handle(self, intent: dict, user_id: str) -> dict:
        action = intent.get("action")
        params = intent.get("params", {})

        if action == "store_memory":
            return self._store(user_id, params)
        elif action == "retrieve_memory":
            return self._retrieve(user_id, params)
        elif action == "delete_memory":
            return self._delete(params)
        else:
            return self._result(
                "I can store or retrieve memories for you. Try 'remember that ...' or 'what do you remember?'",
                ["Context Agent: awaiting valid action"],
            )

    def _store(self, user_id: str, params: dict) -> dict:
        content = params.get("content", "")
        category = params.get("category", "general")
        if not content:
            return self._result("Nothing to remember. Please provide content.", ["Context Agent: empty content"])
        result = save_to_memory(user_id, content, category)
        return self._result(
            f"Stored in memory: '{content}' (category: {category})",
            [
                "Routed to Context Retrieval Agent",
                "Executed INSERT on AlloyDB memory_context table",
                f"Memory ID: {result['id']}",
            ],
            data=result,
        )

    def _retrieve(self, user_id: str, params: dict) -> dict:
        category = params.get("category")
        memories = get_memory(user_id, category)
        if not memories:
            return self._result(
                "No memories found in the database." + (f" (category: {category})" if category else ""),
                ["Routed to Context Retrieval Agent", "Executed SELECT on AlloyDB memory_context table", "0 results"],
            )
        formatted = "\n".join(f"- [{m['category']}] {m['content']} ({m['timestamp']})" for m in memories)
        return self._result(
            f"Retrieved {len(memories)} memories:\n{formatted}",
            [
                "Routed to Context Retrieval Agent",
                "Executed SELECT on AlloyDB memory_context table",
                f"{len(memories)} results returned",
            ],
            data={"memories": memories},
        )

    def _delete(self, params: dict) -> dict:
        memory_id = params.get("id")
        if not memory_id:
            return self._result("No memory ID provided for deletion.", ["Context Agent: missing ID"])
        success = delete_memory(memory_id)
        if success:
            return self._result(
                f"Memory #{memory_id} deleted.",
                ["Routed to Context Retrieval Agent", f"Deleted memory ID {memory_id}"],
            )
        return self._result(f"Memory #{memory_id} not found.", ["Context Agent: ID not found"])
