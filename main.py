"""Set up YouTube live broadcasts for the next upcoming samagam(s): picks
the samagam, generates its thumbnail, works out every stream it needs,
and creates them all on YouTube. If more than one samagam is next up
(overlapping date ranges - e.g. two events double-booked the same
weekend), every one of them is processed, each with its own playlist,
thumbnail, and shared stream key.

Safe to run repeatedly / on a schedule (e.g. GitHub Actions cron):
- Skips a samagam if it's more than DAYS_BEFORE_THRESHOLD days away.
- create_streams_for_samagam() checks each session individually against
  what's already been created (by title, not just "does the playlist
  exist"), so a rerun after a partial failure only creates what's
  actually missing instead of skipping everything or duplicating it.
"""

from datetime import date

from scheduler import load_samagams, get_next_samagams
from thumbnail import generate_thumbnail
from broadcast import build_broadcast_plans, future_plans
from youtube_api import create_streams_for_samagam
from manifest import save_manifest

DAYS_BEFORE_THRESHOLD = 2


def process_samagam(samagam) -> list[dict]:
    print(f"\nSamagam: {samagam.label} ({samagam.start_date} - {samagam.end_date}, {samagam.timezone})\n")

    days_until_start = (samagam.start_date - date.today()).days
    if days_until_start > DAYS_BEFORE_THRESHOLD:
        print(f"Starts in {days_until_start} days - more than {DAYS_BEFORE_THRESHOLD} days out, nothing to do yet.")
        return []

    thumbnail_path = generate_thumbnail(samagam.city, samagam.state, samagam.start_date, samagam.end_date)

    plans = build_broadcast_plans(samagam)
    plans = future_plans(plans)

    if not plans:
        print("\nNo upcoming sessions left for this samagam - nothing to create.")
        return []

    print(f"\n{len(plans)} session(s) to process...\n")
    results = create_streams_for_samagam(plans, thumbnail_path)

    if not results:
        print("\nNothing succeeded this run for this samagam - see errors above.")
        return []

    print("\n=== SUMMARY ===")
    print(f"Samagam: {samagam.label}")
    print(f"Shared stream ID: {results[0]['stream_id']}")
    print(f"Succeeded: {len(results)}/{len(plans)} session(s)")
    for r in results:
        print(f"\n{r['title']}")
        print(f"  Scheduled: {r['scheduled_start']}")
        print(f"  Watch:  {r['watch_url']}")
        print(f"  Studio: {r['studio_url']}")

    return results


def main() -> None:
    samagams = load_samagams()
    next_samagams = get_next_samagams(samagams)

    if len(next_samagams) > 1:
        labels = ", ".join(s.label for s in next_samagams)
        print(f"\n{len(next_samagams)} samagams overlap in date range - processing all of them: {labels}")

    all_results = []
    for samagam in next_samagams:
        all_results.extend(process_samagam(samagam))

    if not all_results:
        return

    save_manifest(all_results)
    print("\nSaved live_manifest.json for the start/stop trigger.")


if __name__ == "__main__":
    main()
