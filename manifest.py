"""Tracks which broadcast is scheduled/live/ended for the samagam most
recently processed. This is what lets an external trigger (the OBS
plugin's start/stop button) know exactly which broadcast to act on -
the same job a human does by eyeballing the clock and picking the right
scheduled event in YouTube Studio, just automated.
"""

import json
from pathlib import Path

MANIFEST_PATH = Path(__file__).parent / "live_manifest.json"


def save_manifest(results: list[dict]) -> None:
    entries = [
        {
            "broadcast_id": r["broadcast_id"],
            "title": r["title"],
            "scheduled_start": r["scheduled_start"],
            "status": "scheduled",
        }
        for r in results
    ]
    write_manifest(entries)


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text())


def write_manifest(entries: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(entries, indent=2))
