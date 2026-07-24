"""Build data/products.json from live Carrefour Egypt prices.

Each catalogue entry names the item a tourist actually buys and the search terms that
find it on Carrefour. For every entry we take the cheapest single-unit match, which
approximates the ordinary shelf price rather than a premium or bulk variant.

Run:  .venv/bin/python scripts/seed_products.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from carrefour import Product, new_session, search  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "products.json"

@dataclass(frozen=True)
class Item:
    """One catalogue entry and the constraints that pin it to the right Carrefour product.

    Carrefour's search is loose -- "water 1.5 liter" returns water *heaters*, "chocolate
    bar" returns gift hampers -- so a name pattern alone is not enough. Each entry also
    declares the size window and a price ceiling it must fall inside.
    """

    id: str
    name: str
    name_ar: str
    category: str
    keyword: str  # what to type into Carrefour's search
    match: str  # regex the product name must contain
    size_range: tuple[int, int] | None  # in ml or grams
    max_egp: float  # sanity ceiling; an FMCG item is never hundreds of EGP
    aliases: list[str]  # what a tourist would actually type
    # Most items are sold singly, but some are only sold in multipacks whose *unit* is the
    # thing a tourist buys -- one pocket tissue pack out of a strip of ten.
    max_pack: int = 3


CATALOGUE = [
    Item("water-600ml", "Water 600ml", "مياه ٦٠٠ مل", "drinks", "water",
         r"water", (500, 700), 40,
         ["water", "bottle", "small water", "aqua", "safi", "maya"]),
    Item("water-15l", "Water 1.5L", "مياه ١.٥ لتر", "drinks", "drinking water 1.5 liter",
         r"water", (1400, 1600), 60,
         ["water", "big water", "dasani", "nestle", "hayat", "baraka"]),
    Item("cola-330ml", "Cola can 330ml", "كولا ٣٣٠ مل", "drinks", "coca cola can",
         r"cola", (300, 360), 60, ["coke", "cola", "coca", "pepsi", "can"]),
    Item("cola-390ml", "Cola bottle 390ml", "كولا ٣٩٠ مل", "drinks", "coca cola bottle",
         r"cola", (380, 400), 60, ["coke", "cola", "pepsi", "soft drink"]),
    Item("chips-small", "Potato chips small bag", "شيبسي صغير", "snacks",
         "chipsy potato chips", r"chips|chipsy", (20, 80), 60,
         ["chips", "crisps", "lays", "chipsy", "snack"]),
    Item("juice-1l", "Juice 1L", "عصير ١ لتر", "drinks", "juice 1 liter",
         r"juice", (900, 1100), 120, ["juice", "orange juice", "mango", "juhayna"]),
    Item("energy-drink", "Energy drink can", "مشروب طاقة", "drinks", "red bull energy",
         r"energy", (240, 500), 120, ["energy", "red bull", "power horse"]),
    # Sunscreen really does cost this much in Egypt -- the cheapest Carrefour stocks is
    # ~190 EGP and the range runs to 380. The high ceiling is correct, not a loose filter.
    Item("sunscreen", "Sunscreen SPF 50", "واقي شمس", "toiletries", "sunscreen spf",
         r"sun(?:screen|block)|spf", (80, 250), 600,
         ["sunscreen", "sunblock", "spf", "sun cream", "nivea"]),
    # Sold as a strip of ten packs; the unit a tourist buys is one pack, hence max_pack=12.
    Item("tissues", "Pocket tissues", "مناديل جيب", "toiletries", "pocket tissues",
         r"pocket tissue", None, 20, ["tissues", "kleenex", "napkins"], max_pack=12),
    Item("chocolate-bar", "Chocolate bar", "لوح شوكولاتة", "snacks", "chocolate bar",
         r"chocolate", (20, 100), 80,
         ["chocolate", "galaxy", "snickers", "kitkat", "candy"]),
    Item("biscuits", "Biscuits pack", "بسكويت", "snacks", "biscuit",
         r"biscuit", None, 60, ["biscuits", "cookies", "oreo"]),
    Item("instant-coffee", "Instant coffee sachet", "قهوة سريعة", "drinks",
         "nescafe sachet", r"coffee|nescafe", None, 60,
         ["coffee", "nescafe", "instant coffee"]),
]

SIZE_PARSE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kilograms?|kg|grams?|gm?|millilitres?|milliliters?|ml|lit(?:re|er)s?|l)",
    re.I,
)


def _to_base(unit: str) -> float:
    """Millilitres for volumes, grams for weights -- both scale by 1000 for the big unit."""
    u = unit.lower()
    if u.startswith(("kg", "kilogram")) or u.startswith(("l", "lit")):
        return 1000.0
    return 1.0


# Carrefour's search is loose: querying "water 1.5 liter" returns water *heaters* and jugs,
# and "chocolate bar" returns hampers. Names alone cannot separate these, so each candidate
# must also survive a sanity ceiling on price -- an FMCG item is never hundreds of EGP.
EXCLUDE_RE = re.compile(
    r"heater|dispenser|jug|kettle|pump|thermal|lunch\s*box|machine|wipers|"
    r"filter|cooler|hamper|gift|basket|mug|tumbler|flask",
    re.I,
)


def size_value(size: str) -> float | None:
    """Normalise a parsed size string to millilitres or grams for comparison."""
    match = SIZE_PARSE_RE.search(size)
    if not match:
        return None
    return float(match.group(1)) * _to_base(match.group(2))


def pick(products: list[Product], item: Item) -> Product | None:
    """Cheapest plausible product satisfying the item's name, size, pack and price limits."""
    pattern = re.compile(item.match, re.I)
    candidates = []
    for p in products:
        if p.pack_count > item.max_pack or not (0 < p.unit_price_egp <= item.max_egp):
            continue
        if not pattern.search(p.name) or EXCLUDE_RE.search(p.name):
            continue
        if item.size_range:
            value = size_value(p.size)
            if value is None or not (item.size_range[0] <= value <= item.size_range[1]):
                continue
        candidates.append(p)
    return min(candidates, key=lambda p: p.unit_price_egp) if candidates else None


def main() -> int:
    session = new_session()
    today = date.today().strftime("%Y-%m")
    entries = []

    for item in CATALOGUE:
        try:
            results = search(item.keyword, session)
        except Exception as exc:  # noqa: BLE001 - one bad query must not kill the run
            print(f"  !! {item.id}: search failed ({exc})", file=sys.stderr)
            continue

        chosen = pick(results, item)
        if not chosen:
            print(
                f"  !! {item.id}: no match among {len(results)} results", file=sys.stderr
            )
            continue

        entries.append({
            "id": item.id,
            "name": item.name,
            "name_ar": item.name_ar,
            "category": item.category,
            "baseline_egp": chosen.unit_price_egp,
            "aliases": item.aliases,
            "source": {
                "store": "Carrefour Egypt",
                "product": chosen.name,
                "url": chosen.url,
                "size": chosen.size,
            },
            "updated": today,
        })
        print(f"  {item.id:16} {chosen.unit_price_egp:>7.2f} EGP  {chosen.name[:46]}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {len(entries)} products -> {OUT.relative_to(ROOT)}")
    return 0 if entries else 1


if __name__ == "__main__":
    raise SystemExit(main())
