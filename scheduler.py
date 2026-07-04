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


def prompt_choice(a: Samagam, b: Samagam) -> Samagam:
    print("Two samagams overlap in date range:")
    print(f"  1) {a.label} ({a.start_date} - {a.end_date})")
    print(f"  2) {b.label} ({b.start_date} - {b.end_date})")
    while True:
        choice = input("Select 1 or 2: ").strip()
        if choice == "1":
            return a
        if choice == "2":
            return b
        print("Please enter 1 or 2.")


def get_next_samagam(samagams: list[Samagam], today: date | None = None) -> Samagam:
    today = today or date.today()

    upcoming = sorted(
        (s for s in samagams if s.end_date >= today),
        key=lambda s: s.start_date,
    )
    if not upcoming:
        raise ValueError("No upcoming samagams found in CSV.")

    if len(upcoming) == 1 or not overlaps(upcoming[0], upcoming[1]):
        return upcoming[0]

    return prompt_choice(upcoming[0], upcoming[1])


def main() -> None:
    samagams = load_samagams()
    next_samagam = get_next_samagam(samagams)
    print(f"\nNext samagam: {next_samagam.label}")
    print(f"Dates: {next_samagam.start_date} - {next_samagam.end_date}")


if __name__ == "__main__":
    main()
