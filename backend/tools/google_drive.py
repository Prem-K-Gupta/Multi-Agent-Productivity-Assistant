"""
Google Drive MCP Tool - Real integration with Google Drive API.
"""

import logging
from tools.mcp_tools import MCPTool
from google_auth import get_service_for_user
from database.alloydb import get_google_token

logger = logging.getLogger(__name__)


class GoogleDriveTool(MCPTool):
    """MCP tool for Google Drive - search and list files."""

    @property
    def name(self) -> str:
        return "google_drive"

    @property
    def description(self) -> str:
        return "Google Drive - search files and list recent documents."

    def _get_service(self, token_json: str):
        return get_service_for_user("drive", "v3", token_json)

    def execute(self, action: str, params: dict) -> dict:
        user_id = params.get("user_id", "default_user")
        token_row = get_google_token(user_id)
        if not token_row:
            return self._error("Google not authenticated. Sign in via the Google login button first.")

        token_json = token_row["token_json"]

        try:
            if action == "search":
                return self._search_files(token_json, params)
            elif action == "list_recent":
                return self._list_recent(token_json, params)
            else:
                return self._error(f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Google Drive error")
            return self._error(str(e))

    def _search_files(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        query = params.get("query", "")
        max_results = params.get("max_results", 10)

        if not query:
            return self._error("Search query is required.")

        results = service.files().list(
            q=f"name contains '{query}' and trashed = false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        file_list = []
        for f in files:
            file_list.append({
                "id": f["id"],
                "name": f["name"],
                "type": f.get("mimeType", ""),
                "modified": f.get("modifiedTime", ""),
                "link": f.get("webViewLink", ""),
            })

        return self._success(f"{len(file_list)} file(s) matching '{query}'.", data={"files": file_list})

    def _list_recent(self, token_json: str, params: dict) -> dict:
        service = self._get_service(token_json)
        max_results = params.get("max_results", 10)

        results = service.files().list(
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
            q="trashed = false",
        ).execute()

        files = results.get("files", [])
        file_list = []
        for f in files:
            file_list.append({
                "id": f["id"],
                "name": f["name"],
                "type": f.get("mimeType", ""),
                "modified": f.get("modifiedTime", ""),
                "link": f.get("webViewLink", ""),
            })

        return self._success(f"{len(file_list)} recent file(s) from Google Drive.", data={"files": file_list})
