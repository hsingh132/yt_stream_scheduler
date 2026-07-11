"""CLI the OBS plugin shells out to when its start/stop button is
pressed:

    python3 live_control.py start
    python3 live_control.py stop

`start` picks whichever scheduled broadcast is closest to right now
(same choice a human makes by eyeballing the clock in YouTube Studio)
and transitions it to live. `stop` ends whichever one is currently live.
Nothing here is time-based once a session is live - it only ends when
`stop` is actually called.
"""

import sys
import time
from datetime import datetime, timezone

from googleapiclient.errors import HttpError

from auth import get_youtube_client
from manifest import load_manifest, write_manifest

# OBS's feed needs a moment to reach YouTube and be detected as healthy
# before a transition to "live" is accepted - retry briefly instead of
# failing immediately if start_stream was just pressed.
TRANSITION_RETRY_ATTEMPTS = 10
TRANSITION_RETRY_DELAY_SECONDS = 3


def _parse(entry: dict) -> datetime:
    return datetime.fromisoformat(entry["scheduled_start"])


def _transition(youtube, broadcast_id: str, status: str) -> None:
    youtube.liveBroadcasts().transition(
        broadcastStatus=status, id=broadcast_id, part="id,status"
    ).execute()


def start() -> None:
    entries = load_manifest()

    if any(e["status"] == "live" for e in entries):
        print("A session is already live - stop it before starting another.")
        sys.exit(1)

    scheduled = [e for e in entries if e["status"] == "scheduled"]
    if not scheduled:
        print("No scheduled sessions left to start.")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    target = min(scheduled, key=lambda e: abs((_parse(e) - now).total_seconds()))
    print(f"Starting: {target['title']}")

    youtube = get_youtube_client()

    last_error = None
    for attempt in range(1, TRANSITION_RETRY_ATTEMPTS + 1):
        try:
            _transition(youtube, target["broadcast_id"], "live")
            target["status"] = "live"
            write_manifest(entries)
            print(f"Live: {target['title']}")
            return
        except HttpError as e:
            last_error = e
            print(f"  Not ready yet (attempt {attempt}/{TRANSITION_RETRY_ATTEMPTS}), retrying...")
            time.sleep(TRANSITION_RETRY_DELAY_SECONDS)

    print(f"Failed to go live after {TRANSITION_RETRY_ATTEMPTS} attempts: {last_error}")
    sys.exit(1)


def stop() -> None:
    entries = load_manifest()
    live = [e for e in entries if e["status"] == "live"]
    if not live:
        print("Nothing is currently live.")
        sys.exit(1)

    target = live[0]
    print(f"Ending: {target['title']}")

    youtube = get_youtube_client()
    try:
        _transition(youtube, target["broadcast_id"], "complete")
    except HttpError as e:
        print(f"Failed to end broadcast: {e}")
        sys.exit(1)

    target["status"] = "ended"
    write_manifest(entries)
    print(f"Ended: {target['title']}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "start":
        start()
    elif action == "stop":
        stop()
    else:
        print("Usage: python3 live_control.py [start|stop]")
        sys.exit(1)
