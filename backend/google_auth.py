"""
Google OAuth2 authentication module.

Handles credential loading, token refresh, and OAuth consent flow
for Google Calendar, Tasks, Gmail, and Drive APIs.
"""

import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

# All scopes needed for our integrations
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.readonly",
]

_credentials = None


def get_credentials() -> Credentials:
    """Get valid Google OAuth2 credentials, refreshing or re-authenticating as needed."""
    global _credentials

    if _credentials and _credentials.valid:
        return _credentials

    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            creds = None

    # Run OAuth flow if no valid credentials
    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Google credentials not found at {CREDENTIALS_FILE}. "
                "Download OAuth2 credentials from Google Cloud Console and save as backend/credentials.json"
            )
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=8090, prompt="consent")

        # Save token for future use
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        logger.info("Google OAuth token saved.")

    _credentials = creds
    return creds


def get_service(api_name: str, api_version: str):
    """Build and return a Google API service client."""
    creds = get_credentials()
    return build(api_name, api_version, credentials=creds)


def is_google_configured() -> bool:
    """Check if Google credentials file exists (doesn't validate token)."""
    return os.path.exists(CREDENTIALS_FILE)


def is_google_authenticated() -> bool:
    """Check if we have a valid (or refreshable) token."""
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.valid:
            return True
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return True
    except Exception:
        return False
    return False
