"""
Gmail MCP Tool - Real integration with Gmail API.
"""

import base64
import logging
from email.mime.text import MIMEText
from tools.mcp_tools import MCPTool
from google_auth import get_service, is_google_authenticated

logger = logging.getLogger(__name__)


class GmailTool(MCPTool):
    """MCP tool for Gmail - read inbox, search emails, send emails."""

    @property
    def name(self) -> str:
        return "gmail"

    @property
    def description(self) -> str:
        return "Gmail - read inbox, search emails, and send messages."

    def _get_service(self):
        return get_service("gmail", "v1")

    def execute(self, action: str, params: dict) -> dict:
        if not is_google_authenticated():
            return self._error("Google not authenticated. Run /api/auth/google first.")

        try:
            if action == "read_inbox":
                return self._read_inbox(params)
            elif action == "search":
                return self._search_emails(params)
            elif action == "send":
                return self._send_email(params)
            else:
                return self._error(f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Gmail error")
            return self._error(str(e))

    def _read_inbox(self, params: dict) -> dict:
        service = self._get_service()
        max_results = params.get("max_results", 10)

        results = service.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        email_list = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            email_list.append({
                "id": msg["id"],
                "from": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "No Subject"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        return self._success(f"{len(email_list)} email(s) from inbox.", data={"emails": email_list})

    def _search_emails(self, params: dict) -> dict:
        service = self._get_service()
        query = params.get("query", "")
        max_results = params.get("max_results", 10)

        if not query:
            return self._error("Search query is required.")

        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        email_list = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            email_list.append({
                "id": msg["id"],
                "from": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "No Subject"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        return self._success(f"{len(email_list)} email(s) matching '{query}'.", data={"emails": email_list})

    def _send_email(self, params: dict) -> dict:
        service = self._get_service()
        to = params.get("to", "")
        subject = params.get("subject", "")
        body = params.get("body", "")

        if not to:
            return self._error("Recipient email address ('to') is required.")
        if not subject:
            return self._error("Email subject is required.")

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return self._success(
            f"Email sent to {to}.",
            data={"id": sent["id"], "to": to, "subject": subject},
        )
