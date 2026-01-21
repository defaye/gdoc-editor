"""
Authentication module for Google Docs API.

Handles OAuth 2.0 authentication flow and credential management.
"""

import os
import json
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required for reading and writing Google Docs
SCOPES = ["https://www.googleapis.com/auth/documents"]

# Default path for storing user credentials
DEFAULT_CREDS_PATH = Path.home() / ".gdoc-credentials.json"


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


def get_credentials(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    creds_path: Optional[Path] = None,
) -> Credentials:
    """
    Get or create Google OAuth credentials.

    Args:
        client_id: Google OAuth client ID (from environment if not provided)
        client_secret: Google OAuth client secret (from environment if not provided)
        creds_path: Path to store/load credentials (default: ~/.gdoc-credentials.json)

    Returns:
        Authenticated credentials object

    Raises:
        AuthenticationError: If authentication fails or credentials are missing
    """
    if creds_path is None:
        creds_path = DEFAULT_CREDS_PATH

    creds = None

    # Try to load existing credentials
    if creds_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(creds_path), SCOPES)
        except Exception as e:
            print(f"Warning: Could not load credentials from {creds_path}: {e}")

    # Refresh or create new credentials
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"Warning: Could not refresh credentials: {e}")
            creds = None

    if not creds or not creds.valid:
        # Get client ID and secret
        client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise AuthenticationError(
                "Missing credentials. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
                "environment variables or pass them as arguments.\n"
                "See README.md for instructions on obtaining OAuth credentials."
            )

        # Create client config for OAuth flow
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"],
            }
        }

        # Run OAuth flow
        try:
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        except Exception as e:
            raise AuthenticationError(f"OAuth flow failed: {e}")

        # Save credentials for future use
        try:
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            with open(creds_path, "w") as f:
                f.write(creds.to_json())
            print(f"Credentials saved to {creds_path}")
        except Exception as e:
            print(f"Warning: Could not save credentials: {e}")

    return creds


def get_docs_service(creds: Optional[Credentials] = None):
    """
    Get an authenticated Google Docs API service.

    Args:
        creds: Existing credentials (will create new ones if not provided)

    Returns:
        Authenticated Google Docs API service object
    """
    if creds is None:
        creds = get_credentials()

    return build("docs", "v1", credentials=creds)


def revoke_credentials(creds_path: Optional[Path] = None) -> bool:
    """
    Revoke and delete stored credentials.

    Args:
        creds_path: Path to credentials file (default: ~/.gdoc-credentials.json)

    Returns:
        True if credentials were deleted, False if they didn't exist
    """
    if creds_path is None:
        creds_path = DEFAULT_CREDS_PATH

    if creds_path.exists():
        creds_path.unlink()
        print(f"Credentials deleted from {creds_path}")
        return True
    else:
        print(f"No credentials found at {creds_path}")
        return False
