"""Session planner: works out how many YouTube streams a samagam needs,
and which day + time-of-day each one covers.

Rule: first day is evening only, last day is morning only, every day in
between gets both a morning and an evening session.
"""

from dataclasses import dataclass
from datetime import date, timedelta

TIMES_OF_DAY = ("morning", "evening")


@dataclass
class Session:
    day: date
    time_of_day: str  # "morning" or "evening"

    @property
    def day_of_week(self) -> str:
        return self.day.strftime("%A")

    @property
    def label(self) -> str:
        return f"{self.day_of_week}, {self.day.strftime('%B')} {self.day.day} - {self.time_of_day.title()}"


def generate_sessions(start: date, end: date) -> list[Session]:
    if start == end:
        raise ValueError(f"Single-day samagam ({start}) isn't supported - first/last day rules conflict.")
    if start > end:
        raise ValueError(f"start_date {start} is after end_date {end}.")

    print(f"[sessions] Building session list for {start} - {end}")

    sessions = []
    day = start
    while day <= end:
        if day == start:
            times = ("evening",)
        elif day == end:
            times = ("morning",)
        else:
            times = TIMES_OF_DAY

        for time_of_day in times:
            session = Session(day=day, time_of_day=time_of_day)
            sessions.append(session)
            print(f"[sessions]   {session.label}")

        day += timedelta(days=1)

    print(f"[sessions] Total sessions: {len(sessions)}")
    return sessions


if __name__ == "__main__":
    generate_sessions(date(2026, 7, 2), date(2026, 7, 5))
