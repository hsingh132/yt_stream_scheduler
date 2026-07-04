"""Run this manually to set up YouTube live broadcasts for the next
upcoming samagam: picks the samagam, generates its thumbnail, works out
every stream it needs, and creates them all on YouTube.
"""

from scheduler import load_samagams, get_next_samagam
from thumbnail import generate_thumbnail
from broadcast import build_broadcast_plans, future_plans
from youtube_api import create_streams_for_samagam


def main() -> None:
    samagams = load_samagams()
    samagam = get_next_samagam(samagams)
    print(f"\nSamagam: {samagam.label} ({samagam.start_date} - {samagam.end_date}, {samagam.timezone})\n")

    thumbnail_path = generate_thumbnail(samagam.city, samagam.state, samagam.start_date, samagam.end_date)

    plans = build_broadcast_plans(samagam)
    plans = future_plans(plans)

    if not plans:
        print("\nNo upcoming sessions left for this samagam - nothing to create.")
        return

    print(f"\n{len(plans)} session(s) to create...\n")
    results = create_streams_for_samagam(plans, thumbnail_path)

    print("\n=== SUMMARY ===")
    print(f"Samagam: {samagam.label}")
    print(f"Shared stream ID: {results[0]['stream_id']}")
    for r in results:
        print(f"\n{r['title']}")
        print(f"  Scheduled: {r['scheduled_start']}")
        print(f"  Watch:  {r['watch_url']}")
        print(f"  Studio: {r['studio_url']}")


if __name__ == "__main__":
    main()
