from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all sub-agents in the system."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def handle(self, intent: dict, user_id: str) -> dict:
        """
        Process an intent and return a result.

        Args:
            intent: Parsed intent dict with 'action', 'params', etc.
            user_id: The user making the request.

        Returns:
            dict with 'message', 'actions', 'data' keys.
        """
        pass

    def _result(self, message: str, actions: list, data: dict = None) -> dict:
        return {
            "message": message,
            "actions": actions,
            "agent": self.name,
            "data": data or {},
        }
