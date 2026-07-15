"""Actual YouTube Data API calls: creates the stream + broadcast pair for
each session, binds them, sets the thumbnail/category, and files
everything into the samagam's playlist.

Nothing in here runs on import - call create_streams_for_samagam()
explicitly once you're ready to actually create real broadcasts.
"""

import time
from pathlib import Path

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from auth import get_youtube_client
from broadcast import BroadcastPlan

THUMBNAIL_RETRY_ATTEMPTS = 3
THUMBNAIL_RETRY_DELAY_SECONDS = 5


def find_playlist(youtube, playlist_name: str) -> str | None:
    request = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            if item["snippet"]["title"] == playlist_name:
                return item["id"]
        request = youtube.playlists().list_next(request, response)
    return None


def find_or_create_playlist(youtube, playlist_name: str) -> str:
    print(f"[youtube] Looking for existing playlist: {playlist_name}")
    existing_id = find_playlist(youtube, playlist_name)
    if existing_id:
        print(f"[youtube]   Found existing playlist: {existing_id}")
        return existing_id

    print(f"[youtube]   Not found, creating playlist: {playlist_name}")
    response = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": playlist_name},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    print(f"[youtube]   Created playlist: {response['id']}")
    return response["id"]


def create_stream(youtube, title: str, resolution: str, frame_rate: str) -> str:
    response = youtube.liveStreams().insert(
        part="snippet,cdn",
        body={
            "snippet": {"title": title},
            "cdn": {
                "ingestionType": "rtmp",
                "resolution": resolution,
                "frameRate": frame_rate,
            },
        },
    ).execute()
    return response["id"]


def create_broadcast(youtube, plan: BroadcastPlan) -> str:
    response = youtube.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": plan.title,
                "description": plan.description,
                "scheduledStartTime": plan.scheduled_start.isoformat(),
            },
            "status": {
                "privacyStatus": plan.privacy_status,
                "selfDeclaredMadeForKids": plan.made_for_kids,
            },
            "contentDetails": {
                # Off on purpose: going live/ending is controlled by an
                # explicit trigger elsewhere, not by YouTube's own stream
                # health detection (which would end the broadcast on a
                # brief OBS disconnect, not just a real stop).
                "enableAutoStart": False,
                "enableAutoStop": False,
                "enableDvr": True,
                "enableLiveChat": plan.enable_live_chat,
                "latencyPreference": plan.latency_preference,
            },
        },
    ).execute()
    return response["id"]


def bind_stream_to_broadcast(youtube, broadcast_id: str, stream_id: str) -> None:
    youtube.liveBroadcasts().bind(
        id=broadcast_id, part="id,contentDetails", streamId=stream_id
    ).execute()


def set_category(youtube, video_id: str, category_id: str) -> None:
    video = youtube.videos().list(part="snippet", id=video_id).execute()["items"][0]
    snippet = video["snippet"]
    snippet["categoryId"] = category_id
    youtube.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()


def set_thumbnail(youtube, video_id: str, thumbnail_path: Path) -> None:
    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))).execute()


def _set_thumbnail_with_retry(youtube, video_id: str, thumbnail_path: Path) -> None:
    """thumbnails.set has been observed to fail transiently (e.g. right
    after a daily access-token refresh) - retry a few times before
    giving up, instead of letting one flaky call abort the whole run."""
    last_error = None
    for attempt in range(1, THUMBNAIL_RETRY_ATTEMPTS + 1):
        try:
            set_thumbnail(youtube, video_id, thumbnail_path)
            return
        except HttpError as e:
            last_error = e
            if attempt < THUMBNAIL_RETRY_ATTEMPTS:
                print(f"[youtube]   Thumbnail upload failed (attempt {attempt}/{THUMBNAIL_RETRY_ATTEMPTS}), retrying...")
                time.sleep(THUMBNAIL_RETRY_DELAY_SECONDS)
    raise last_error


def add_to_playlist(youtube, playlist_id: str, video_id: str) -> None:
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()


def get_playlist_video_ids(youtube, playlist_id: str) -> set[str]:
    ids = set()
    request = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50)
    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            ids.add(item["snippet"]["resourceId"]["videoId"])
        request = youtube.playlistItems().list_next(request, response)
    return ids


def find_existing_broadcasts(youtube, title_prefix: str) -> dict[str, dict]:
    """Broadcasts already created for this samagam, found by title
    rather than playlist membership - so a broadcast that got created
    but never made it into the playlist (e.g. a crash mid-run) still
    counts as "already exists" instead of getting silently ignored or
    duplicated on a resumed run."""
    found = {}
    for status in ("upcoming", "active", "completed"):
        response = youtube.liveBroadcasts().list(
            part="snippet,contentDetails", broadcastStatus=status, maxResults=50
        ).execute()
        for item in response.get("items", []):
            title = item["snippet"]["title"]
            if title.startswith(title_prefix):
                found[title] = {
                    "broadcast_id": item["id"],
                    "stream_id": item["contentDetails"].get("boundStreamId"),
                }
    return found


def create_streams_for_samagam(plans: list[BroadcastPlan], thumbnail_path: Path) -> list[dict]:
    youtube = get_youtube_client()
    playlist_name = plans[0].playlist_name
    playlist_id = find_or_create_playlist(youtube, playlist_name)
    playlist_video_ids = get_playlist_video_ids(youtube, playlist_id)

    # Title prefix shared by every session of this samagam, e.g.
    # "LIVE San Francisco Sadhsangat Samagam 2026" - used to find any
    # broadcasts already created for it, so a resumed run after a
    # partial failure only creates what's actually missing.
    title_prefix = plans[0].title.split(" | Day ")[0]
    existing = find_existing_broadcasts(youtube, title_prefix)

    # One shared, persistent stream key for the whole samagam - bound to
    # every broadcast below. YouTube auto-starts each broadcast at its own
    # scheduledStartTime as long as this key is actively receiving video
    # at that moment, so OBS only needs to be configured once. Reuse the
    # stream from an already-existing broadcast rather than minting a
    # second key for the same samagam.
    stream_id = next((e["stream_id"] for e in existing.values() if e["stream_id"]), None)
    if stream_id:
        print(f"[youtube] Reusing existing shared stream: {stream_id}")
    else:
        stream_title = f"{playlist_name} Stream"
        stream_id = create_stream(youtube, stream_title, plans[0].resolution, plans[0].frame_rate)
        print(f"[youtube] Shared stream created: {stream_id}")

    results = []
    for i, plan in enumerate(plans, start=1):
        existing_entry = existing.get(plan.title)

        try:
            if existing_entry:
                broadcast_id = existing_entry["broadcast_id"]
                print(f"[youtube] ({i}/{len(plans)}) Already exists: {plan.title}")
                # Repair any step a previous partial failure might have
                # skipped - both are safe to redo even if already done.
                _set_thumbnail_with_retry(youtube, broadcast_id, thumbnail_path)
                if broadcast_id not in playlist_video_ids:
                    add_to_playlist(youtube, playlist_id, broadcast_id)
                    print(f"[youtube]   Added to playlist (was missing): {playlist_name}")
            else:
                print(f"[youtube] ({i}/{len(plans)}) Creating: {plan.title}")

                broadcast_id = create_broadcast(youtube, plan)
                print(f"[youtube]   Broadcast created: {broadcast_id}")

                bind_stream_to_broadcast(youtube, broadcast_id, stream_id)
                print("[youtube]   Bound stream to broadcast")

                set_category(youtube, broadcast_id, plan.category_id)
                print(f"[youtube]   Category set: {plan.category_id}")

                _set_thumbnail_with_retry(youtube, broadcast_id, thumbnail_path)
                print("[youtube]   Thumbnail attached")

                add_to_playlist(youtube, playlist_id, broadcast_id)
                print(f"[youtube]   Added to playlist: {playlist_name}")

            results.append({
                "title": plan.title,
                "scheduled_start": plan.scheduled_start.isoformat(),
                "watch_url": f"https://youtube.com/watch?v={broadcast_id}",
                "studio_url": f"https://studio.youtube.com/video/{broadcast_id}/livestreaming",
                "stream_id": stream_id,
                "broadcast_id": broadcast_id,
            })
        except HttpError as e:
            print(f"[youtube]   FAILED: {e}")
            print("[youtube]   Skipping this session for now - a later rerun will only retry this one.")
            continue

    return results
