"""YouTube OAuth: handles the one-time browser consent and reuses the
saved token on every run after that.

Run this file directly to do the first-time authorization. Other modules
should just call get_youtube_client().
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

BASE_DIR = Path(__file__).parent
CLIENT_SECRET_PATH = BASE_DIR / "client_secret.json"
TOKEN_PATH = BASE_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def get_credentials() -> Credentials:
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        print("[auth] Access token expired, refreshing...")
        creds.refresh(Request())
    else:
        print("[auth] No saved token found - opening browser for one-time authorization...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    print(f"[auth] Token saved to {TOKEN_PATH}")
    return creds


def get_youtube_client() -> Resource:
    creds = get_credentials()
    return build("youtube", "v3", credentials=creds)


if __name__ == "__main__":
    youtube = get_youtube_client()
    response = youtube.channels().list(part="snippet", mine=True).execute()
    channel = response["items"][0]["snippet"]
    print(f"[auth] Authorized for channel: {channel['title']}")
