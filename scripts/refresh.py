"""Weekly price refresh with a human-reviewable drift report.

Egyptian inflation moves fast, so baselines go stale. This re-scrapes Carrefour and
compares against the committed data/products.json.

    --check   report drift and write nothing (used by CI to open an issue)
    (default) rewrite data/products.json with the fresh prices

Prices are never silently rewritten in CI: a scrape failure or a Carrefour redesign must
not quietly poison the baselines a tourist relies on. CI reports; a human merges.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from seed_products import CATALOGUE, OUT, ROOT, pick  # noqa: E402
from carrefour import new_session, search  # noqa: E402

# Report anything that moved by more than this fraction; smaller wobbles are noise.
DRIFT_THRESHOLD = 0.10


def load_current() -> dict[str, float]:
    if not OUT.exists():
        return {}
    data = json.loads(OUT.read_text(encoding="utf-8"))
    return {entry["id"]: float(entry["baseline_egp"]) for entry in data}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = parser.parse_args()

    current = load_current()
    session = new_session()
    rows: list[tuple[str, float | None, float | None]] = []
    failures: list[str] = []

    for item in CATALOGUE:
        try:
            chosen = pick(search(item.keyword, session), item)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{item.id}: {exc}")
            chosen = None
        rows.append((item.id, current.get(item.id), chosen.unit_price_egp if chosen else None))

    drifted = [
        (pid, old, new)
        for pid, old, new in rows
        if old and new and abs(new - old) / old > DRIFT_THRESHOLD
    ]
    missing = [pid for pid, _o, new in rows if new is None]

    print(f"checked {len(rows)} products against {OUT.relative_to(ROOT)}\n")
    if drifted:
        print("PRICE DRIFT (>10%):")
        for pid, old, new in drifted:
            pct = (new - old) / old * 100
            print(f"  {pid:16} {old:>7.2f} -> {new:>7.2f} EGP  ({pct:+.0f}%)")
    else:
        print("no drift beyond 10%")

    if missing:
        print(f"\nNO MATCH FOUND: {', '.join(missing)}")
        print("  (Carrefour search results or markup may have changed)")
    if failures:
        print("\nERRORS:")
        for f in failures:
            print(f"  {f}")

    if args.check:
        # Non-zero tells CI there is something for a human to look at.
        return 1 if (drifted or missing or failures) else 0

    # Rewriting delegates to the seeder so there is exactly one place that builds the file.
    from seed_products import main as seed_main

    return seed_main()


if __name__ == "__main__":
    raise SystemExit(main())
