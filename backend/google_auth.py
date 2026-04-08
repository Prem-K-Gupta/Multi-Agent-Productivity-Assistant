"""
Google OAuth2 authentication module - Web Server Flow.

Designed for Cloud Run deployment where every user can independently
sign in with their own Google Account. Tokens are stored per-user in
the SQLite database so each user only sees their own Calendar/Gmail/Drive.
"""

import os
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Allow scope changes — Google may grant fewer scopes than requested
# (e.g. if APIs aren't enabled). oauthlib raises a Warning by default.
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")

# All scopes needed for our integrations
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def is_google_configured() -> bool:
    """Check if Google credentials.json file exists."""
    return os.path.exists(CREDENTIALS_FILE)


def build_oauth_flow(redirect_uri: str) -> Flow:
    """Build the OAuth2 Web Server Flow with the given redirect URI."""
    if not is_google_configured():
        raise FileNotFoundError(
            "credentials.json not found in backend/. "
            "Download OAuth2 Web App credentials from Google Cloud Console."
        )
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


def get_authorization_url(redirect_uri: str, state: str = None) -> str:
    """Generate a Google OAuth authorization URL to redirect the user to."""
    flow = build_oauth_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state or "nexus_auth",
    )
    return auth_url


def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    """
    Exchange the authorization code from Google for access + refresh tokens.
    Returns a dict with token_json and user email.
    """
    flow = build_oauth_flow(redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Get user info (email)
    user_info_service = build("oauth2", "v2", credentials=creds)
    user_info = user_info_service.userinfo().get().execute()
    email = user_info.get("email", "unknown")

    return {
        "token_json": creds.to_json(),
        "email": email,
        "name": user_info.get("name", email),
    }


def get_credentials_for_user(token_json: str) -> Credentials:
    """
    Rebuild a Credentials object from a stored token JSON string.
    Automatically refreshes if expired.
    """
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Google credentials are invalid and cannot be refreshed. User must re-authenticate.")

    return creds


def get_service_for_user(api_name: str, api_version: str, token_json: str):
    """Build and return a Google API service client for a specific user."""
    creds = get_credentials_for_user(token_json)
    return build(api_name, api_version, credentials=creds)


def google_tools_available_for_user(token_json: str | None) -> bool:
    """Check if a user has valid Google tokens."""
    if not token_json:
        return False
    try:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        return creds.valid or bool(creds.refresh_token)
    except Exception:
        return False
