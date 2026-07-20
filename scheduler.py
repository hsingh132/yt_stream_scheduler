"""YouTube samagam stream scheduler.

Run this script manually to figure out which samagam is next up.
More pipeline steps (thumbnail generation, stream/broadcast creation)
will be added to this same file as they get locked in.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

CSV_PATH = Path(__file__).parent / "samagams.csv"
DATE_FORMAT = "%Y-%m-%d"


@dataclass
class Samagam:
    city: str
    state: str
    country: str
    start_date: date
    end_date: date
    timezone: str

    @property
    def label(self) -> str:
        return f"{self.city}, {self.state}" if self.state else self.city


def load_samagams(csv_path: Path = CSV_PATH) -> list[Samagam]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        return [
            Samagam(
                city=row["city"],
                state=row["state"],
                country=row["country"],
                start_date=datetime.strptime(row["start_date"], DATE_FORMAT).date(),
                end_date=datetime.strptime(row["end_date"], DATE_FORMAT).date(),
                timezone=row["timezone"],
            )
            for row in rows
        ]


def overlaps(a: Samagam, b: Samagam) -> bool:
    return a.start_date <= b.end_date and b.start_date <= a.end_date


def get_next_samagams(samagams: list[Samagam], today: date | None = None) -> list[Samagam]:
    """Returns the soonest upcoming samagam, plus any others chained to it
    by overlapping date ranges (e.g. two events double-booked the same
    weekend) - all of them get streamed rather than picking just one."""
    today = today or date.today()

    upcoming = sorted(
        (s for s in samagams if s.end_date >= today),
        key=lambda s: s.start_date,
    )
    if not upcoming:
        raise ValueError("No upcoming samagams found in CSV.")

    group = [upcoming[0]]
    for samagam in upcoming[1:]:
        if any(overlaps(samagam, g) for g in group):
            group.append(samagam)
        else:
            break
    return group


def main() -> None:
    samagams = load_samagams()
    next_samagams = get_next_samagams(samagams)
    for samagam in next_samagams:
        print(f"\nNext samagam: {samagam.label}")
        print(f"Dates: {samagam.start_date} - {samagam.end_date}")


if __name__ == "__main__":
    main()
