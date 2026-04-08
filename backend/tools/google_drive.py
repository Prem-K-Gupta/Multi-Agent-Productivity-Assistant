"""
Google Drive MCP Tool - Real integration with Google Drive API.
"""

import logging
from tools.mcp_tools import MCPTool
from google_auth import get_service, is_google_authenticated

logger = logging.getLogger(__name__)


class GoogleDriveTool(MCPTool):
    """MCP tool for Google Drive - search and list files."""

    @property
    def name(self) -> str:
        return "google_drive"

    @property
    def description(self) -> str:
        return "Google Drive - search files and list recent documents."

    def _get_service(self):
        return get_service("drive", "v3")

    def execute(self, action: str, params: dict) -> dict:
        if not is_google_authenticated():
            return self._error("Google not authenticated. Run /api/auth/google first.")

        try:
            if action == "search":
                return self._search_files(params)
            elif action == "list_recent":
                return self._list_recent(params)
            else:
                return self._error(f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Google Drive error")
            return self._error(str(e))

    def _search_files(self, params: dict) -> dict:
        service = self._get_service()
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

    def _list_recent(self, params: dict) -> dict:
        service = self._get_service()
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
