"""Cross-check committed Carrefour baselines against Spinneys Egypt.

A single source can be wrong in ways that look perfectly reasonable: a misparsed pack
count, a multipack read as a single unit, a decimal in the wrong place. None of those are
visible from inside one dataset. A second, independent chain catches them -- if Carrefour
says 9 EGP and Spinneys says 90, something is broken regardless of which is right.

This reports; it never edits prices. Chains genuinely price differently, so a disagreement
is a prompt to look, not a number to average.

    .venv/bin/python scripts/crosscheck.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from seed_products import CATALOGUE, OUT, size_value  # noqa: E402
from spinneys import browser, search  # noqa: E402

# Below this the two stores broadly agree; above it, suspect a parsing error.
DISAGREEMENT = 0.40
# Spinneys sizes are written loosely, so allow a wide band when matching the variant.
SIZE_TOLERANCE = 0.25


def best_match(products, item):
    """Closest Spinneys product to a catalogue item, preferring the nearest size.

    Picking the cheapest match compares a 4-finger KitKat against a 2-finger one and
    reports a 45% "disagreement" that is really just a smaller bar. Choosing the closest
    size first, then comparing per gram, removes that whole class of false alarm.
    """
    pattern = re.compile(item.match, re.I)
    candidates = [p for p in products if pattern.search(p.name)]
    if item.exclude:
        candidates = [p for p in candidates if not re.search(item.exclude, p.name, re.I)]
    if not candidates:
        return None

    if item.size_range:
        target = sum(item.size_range) / 2
        sized = [(p, size_value(p.size)) for p in candidates]
        sized = [(p, v) for p, v in sized if v]
        if sized:
            return min(sized, key=lambda pair: abs(pair[1] - target))[0]

    return min(candidates, key=lambda p: p.unit_price_egp)


def main() -> int:
    baselines = {e["id"]: float(e["baseline_egp"]) for e in json.loads(OUT.read_text())}
    flagged, compared, missing = [], 0, []

    with browser() as instance:
        for item in CATALOGUE:
            if item.id not in baselines:
                continue
            try:
                found = best_match(search(item.keyword, instance), item)
            except Exception as exc:  # noqa: BLE001 - one failure must not stop the sweep
                print(f"  !! {item.id}: {exc}", file=sys.stderr)
                continue
            if not found:
                missing.append(item.id)
                continue

            compared += 1
            carrefour = baselines[item.id]

            # Compare per gram/millilitre where both sizes are known, so a smaller pack at
            # a proportionally smaller price registers as agreement rather than a gap.
            our_size = next(
                (size_value(e["source"]["size"])
                 for e in json.loads(OUT.read_text()) if e["id"] == item.id),
                None,
            )
            their_size = size_value(found.size)
            if our_size and their_size:
                ours, theirs = carrefour / our_size, found.unit_price_egp / their_size
            else:
                ours, theirs = carrefour, found.unit_price_egp
            gap = abs(theirs - ours) / ours
            flag = "  <-- CHECK" if gap > DISAGREEMENT else ""
            if flag:
                flagged.append(item.id)
            # Print the matched Spinneys product: most disagreements turn out to be a
            # different pack size rather than a bad price, and that is only visible here.
            print(
                f"  {item.id:20} carrefour {carrefour:>7.2f}   spinneys {found.unit_price_egp:>7.2f}"
                f"   {gap * 100:>5.0f}%{flag}\n"
                f"  {'':20} spinneys item: {found.name[:60]}"
            )

    print(f"\ncompared {compared} products against Spinneys")
    if missing:
        print(f"not stocked / not matched at Spinneys: {', '.join(missing)}")
    if flagged:
        print(f"\ndisagree by more than {DISAGREEMENT:.0%}: {', '.join(flagged)}")
        print("A large gap usually means a parsing error, not a real price difference.")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
