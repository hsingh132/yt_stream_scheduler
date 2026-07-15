"""Broadcast planner: builds the exact title, schedule, and fixed settings
for every YouTube stream a samagam needs.

This produces plain data (BroadcastPlan objects) - the actual API calls
(liveBroadcasts.insert, liveStreams.insert, thumbnails.set, playlists,
etc.) get wired in once YouTube OAuth is set up.

`scheduled_start` is timezone-aware, set to the samagam venue's local
time (e.g. "5:00 AM America/Los_Angeles"), not the machine running the
script. Its `.isoformat()` is already the correct RFC3339 string the
YouTube API expects for scheduledStartTime.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from scheduler import Samagam
from sessions import Session, generate_sessions

MORNING_START = time(5, 0)
EVENING_START = time(15, 30)
FIRST_DAY_EVENING_START = time(17, 0)

# Fixed settings, same for every stream every run.
CATEGORY_ID = "24"  # Entertainment
PRIVACY_STATUS = "public"
MADE_FOR_KIDS = False
LATENCY_PREFERENCE = "normal"
RESOLUTION = "variable"
FRAME_RATE = "variable"
DESCRIPTION = ""
BROADCAST_TYPE = "streaming_software"  # RTMP/encoder ingestion, not webcam/mobile

# Desired chat/interaction settings. NOTE: none of these are enforceable
# through the YouTube Data API - it exposes no fields for them (the old
# enableLiveChat field was removed and is silently ignored if sent).
# They document intent only; each must be set by hand in YouTube Studio
# after the broadcasts are created.
ENABLE_LIVE_CHAT = False
ENABLE_LIVE_CHAT_REPLAY = False
ENABLE_LIVE_CHAT_SUMMARY = False
ENABLE_LIVE_CHAT_TRANSLATION = False
ENABLE_LEADERBOARD = False
PARTICIPANT_MODE = "anyone"
ENABLE_LIVE_REACTIONS = False
ENABLE_SLOW_MODE = False


@dataclass
class BroadcastPlan:
    title: str
    scheduled_start: datetime
    playlist_name: str
    description: str = DESCRIPTION
    privacy_status: str = PRIVACY_STATUS
    category_id: str = CATEGORY_ID
    made_for_kids: bool = MADE_FOR_KIDS
    latency_preference: str = LATENCY_PREFERENCE
    resolution: str = RESOLUTION
    frame_rate: str = FRAME_RATE
    broadcast_type: str = BROADCAST_TYPE
    enable_live_chat: bool = ENABLE_LIVE_CHAT
    enable_live_chat_replay: bool = ENABLE_LIVE_CHAT_REPLAY
    enable_live_chat_summary: bool = ENABLE_LIVE_CHAT_SUMMARY
    enable_live_chat_translation: bool = ENABLE_LIVE_CHAT_TRANSLATION
    enable_leaderboard: bool = ENABLE_LEADERBOARD
    participant_mode: str = PARTICIPANT_MODE
    enable_live_reactions: bool = ENABLE_LIVE_REACTIONS
    enable_slow_mode: bool = ENABLE_SLOW_MODE


def _session_time(session: Session, samagam_start: date) -> time:
    if session.time_of_day == "morning":
        return MORNING_START
    if session.day == samagam_start:
        return FIRST_DAY_EVENING_START
    return EVENING_START


def _day_number(session: Session, samagam_start: date) -> int:
    return (session.day - samagam_start).days + 1


def _session_label(session: Session) -> str:
    return "Morn" if session.time_of_day == "morning" else "Eve"


def build_title(city: str, samagam_start: date, session: Session) -> str:
    day_number = _day_number(session, samagam_start)
    date_str = f"{session.day.day} {session.day.strftime('%B')}'{session.day.strftime('%y')}"
    weekday_abbrev = session.day.strftime("%a")
    return (
        f"LIVE {city} Sadhsangat Samagam {session.day.year} | "
        f"Day {day_number} | {date_str} | {weekday_abbrev} {_session_label(session)}"
    )


def build_playlist_name(city: str, year: int) -> str:
    return f"{city} {year} Samagam"


def build_broadcast_plans(samagam: Samagam) -> list[BroadcastPlan]:
    print(f"[broadcast] Building broadcast plans for {samagam.label} ({samagam.start_date} - {samagam.end_date}, {samagam.timezone})")

    sessions = generate_sessions(samagam.start_date, samagam.end_date)
    playlist_name = build_playlist_name(samagam.city, samagam.start_date.year)
    tz = ZoneInfo(samagam.timezone)

    plans = []
    for session in sessions:
        title = build_title(samagam.city, samagam.start_date, session)
        local_time = _session_time(session, samagam.start_date)
        scheduled_start = datetime.combine(session.day, local_time, tzinfo=tz)
        plan = BroadcastPlan(title=title, scheduled_start=scheduled_start, playlist_name=playlist_name)
        plans.append(plan)
        print(f"[broadcast]   {plan.title}  ->  {plan.scheduled_start.isoformat()}")

    print(f"[broadcast] Playlist: {playlist_name}")
    return plans


def future_plans(plans: list[BroadcastPlan]) -> list[BroadcastPlan]:
    """Drops sessions whose start time has already passed - YouTube
    rejects scheduling a broadcast in the past, which happens whenever the
    script runs mid-samagam instead of before it starts."""
    kept = []
    for plan in plans:
        now = datetime.now(plan.scheduled_start.tzinfo)
        if plan.scheduled_start > now:
            kept.append(plan)
        else:
            print(f"[broadcast]   Skipping (already started): {plan.title}")
    return kept


if __name__ == "__main__":
    test_samagam = Samagam(
        city="San Francisco",
        state="CA",
        country="USA",
        start_date=date(2026, 7, 2),
        end_date=date(2026, 7, 5),
        timezone="America/Los_Angeles",
    )
    build_broadcast_plans(test_samagam)
