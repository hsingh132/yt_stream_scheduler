"""Set up YouTube live broadcasts for the next upcoming samagam: picks
the samagam, generates its thumbnail, works out every stream it needs,
and creates them all on YouTube.

Safe to run repeatedly / on a schedule (e.g. GitHub Actions cron):
- Does nothing if the next samagam is more than DAYS_BEFORE_THRESHOLD
  days away.
- create_streams_for_samagam() checks each session individually against
  what's already been created (by title, not just "does the playlist
  exist"), so a rerun after a partial failure only creates what's
  actually missing instead of skipping everything or duplicating it.
"""

from datetime import date

from scheduler import load_samagams, get_next_samagam
from thumbnail import generate_thumbnail
from broadcast import build_broadcast_plans, future_plans
from youtube_api import create_streams_for_samagam
from manifest import save_manifest

DAYS_BEFORE_THRESHOLD = 2


def main() -> None:
    samagams = load_samagams()
    samagam = get_next_samagam(samagams)
    print(f"\nSamagam: {samagam.label} ({samagam.start_date} - {samagam.end_date}, {samagam.timezone})\n")

    days_until_start = (samagam.start_date - date.today()).days
    if days_until_start > DAYS_BEFORE_THRESHOLD:
        print(f"Starts in {days_until_start} days - more than {DAYS_BEFORE_THRESHOLD} days out, nothing to do yet.")
        return

    thumbnail_path = generate_thumbnail(samagam.city, samagam.state, samagam.start_date, samagam.end_date)

    plans = build_broadcast_plans(samagam)
    plans = future_plans(plans)

    if not plans:
        print("\nNo upcoming sessions left for this samagam - nothing to create.")
        return

    print(f"\n{len(plans)} session(s) to process...\n")
    results = create_streams_for_samagam(plans, thumbnail_path)

    if not results:
        print("\nNothing succeeded this run - see errors above.")
        return

    save_manifest(results)
    print("\nSaved live_manifest.json for the start/stop trigger.")

    print("\n=== SUMMARY ===")
    print(f"Samagam: {samagam.label}")
    print(f"Shared stream ID: {results[0]['stream_id']}")
    print(f"Succeeded: {len(results)}/{len(plans)} session(s)")
    for r in results:
        print(f"\n{r['title']}")
        print(f"  Scheduled: {r['scheduled_start']}")
        print(f"  Watch:  {r['watch_url']}")
        print(f"  Studio: {r['studio_url']}")


if __name__ == "__main__":
    main()
