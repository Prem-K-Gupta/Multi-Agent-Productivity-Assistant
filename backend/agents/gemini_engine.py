"""
Gemini-powered natural language understanding engine.

Uses Google's Gemini API for:
1. Intent classification - determines which agent should handle the request
2. Parameter extraction - pulls structured data from natural language
3. Response generation - creates natural conversational responses
"""

import os
import json
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_client = None


def _get_client():
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set in environment. Add it to backend/.env")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def is_gemini_configured() -> bool:
    """Check if Gemini API key is available."""
    return bool(GEMINI_API_KEY)


INTENT_PROMPT = """You are an intent classifier for a productivity assistant. Given the user's message, return a JSON object with:

- "agent": one of "task", "schedule", "context", "notes", "gmail", "drive", "workflow", "help", or "general"
- "action": the specific action (see below)
- "params": extracted parameters as a dict

Agent actions:
- task: create_task, list_tasks, update_task, complete_task, delete_task
- schedule: create_event, list_events, delete_event
- context: store_memory, retrieve_memory, delete_memory
- notes: create_note, list_notes, update_note, delete_note
- gmail: read_inbox, search_emails, send_email
- drive: search_files, list_recent
- workflow: plan_my_day, weekly_review
- help: show_help
- general: chat (for general conversation)

Parameter extraction rules:
- For tasks: extract "title", "description", "priority" (high/medium/low), "due_date"
- For events: extract "title", "start_time", "end_time", "location", "description"
- For memory: extract "content", "category"
- For notes: extract "title", "content", "tags"
- For gmail: extract "query" (search terms), "to", "subject", "body", "max_results"
- For drive: extract "query", "max_results"
- For complete/delete: extract "id" as integer if mentioned
- For workflows: no params needed

Return ONLY valid JSON with no markdown formatting, no backticks. Example:
{"agent": "task", "action": "create_task", "params": {"title": "Buy groceries", "priority": "high"}}

User message: """


def parse_intent(user_message: str) -> dict:
    """Use Gemini to parse user intent from natural language."""
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=INTENT_PROMPT + user_message,
            config={
                "temperature": 0.1,
                "max_output_tokens": 300,
            },
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        parsed = json.loads(text)
        logger.info(f"Gemini intent: {parsed}")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {text} - {e}")
        return {"agent": "general", "action": "chat", "params": {"raw": user_message}}
    except Exception as e:
        logger.error(f"Gemini parse_intent failed: {e}")
        return {"agent": "general", "action": "chat", "params": {"raw": user_message}}


RESPONSE_PROMPT = """You are Nexus, a helpful productivity assistant. Given the action result below, write a brief, friendly response to the user. Be concise (1-3 sentences). Don't use markdown headers or excessive formatting.

Action performed: {action}
Agent: {agent}
Result data: {data}

User's original message: {user_message}

Write a natural response:"""


def generate_response(action: str, agent: str, data: dict, user_message: str) -> str:
    """Use Gemini to generate a natural language response from structured data."""
    try:
        client = _get_client()
        prompt = RESPONSE_PROMPT.format(
            action=action,
            agent=agent,
            data=json.dumps(data, default=str)[:1000],
            user_message=user_message,
        )
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config={
                "temperature": 0.7,
                "max_output_tokens": 300,
            },
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini generate_response failed: {e}")
        return None


def chat_response(user_message: str, context: str = "") -> str:
    """Generate a general conversational response."""
    try:
        client = _get_client()
        prompt = (
            "You are Nexus, a multi-agent productivity assistant. You help with tasks, "
            "calendar, email, notes, and memory. Be brief and helpful.\n\n"
        )
        if context:
            prompt += f"Context: {context}\n\n"
        prompt += f"User: {user_message}\nNexus:"

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config={
                "temperature": 0.7,
                "max_output_tokens": 400,
            },
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini chat failed: {e}")
        return f"I'm your Nexus Orchestrator. I can help with tasks, calendar, email, notes, and memory. You said: '{user_message}'"
