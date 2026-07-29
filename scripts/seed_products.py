"""Build data/products.json from live Carrefour Egypt prices.

Each catalogue entry names the item a tourist actually buys and the search terms that
find it on Carrefour. For every entry we take the cheapest single-unit match, which
approximates the ordinary shelf price rather than a premium or bulk variant.

Run:  .venv/bin/python scripts/seed_products.py
"""

from __future__ import annotations

import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from carrefour import Product, fetch_image_urls, is_in_stock, new_session, search  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "products.json"
IMAGE_DIR = ROOT / "public" / "products"

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
    # Sanity floor. A chocolate bar is never 2.50 EGP -- that figure only appears when a
    # 24-piece box is misread as 24 separate bars, which no size or pack rule catches.
    min_egp: float = 0.0
    # Most items are sold singly, but some are only sold in multipacks whose *unit* is the
    # thing a tourist buys -- one pocket tissue pack out of a strip of ten.
    max_pack: int = 3
    # Brand-level exclusion for line extensions that share the brand name but are a
    # different product -- "Galaxy Flutes" wafer rolls are not a Galaxy chocolate bar.
    exclude: str = ""
    # Photo handling. "" picks automatically; "-" means Carrefour has no usable packshot
    # for this product, so show nothing rather than a misleading image. No heuristic can
    # tell a mineral-composition table from a bottle reliably, so the few bad cases are
    # curated by eye instead of guessed at.
    image_url: str = ""


# Flavour and diet line extensions cost more (or less) than the standard product and are
# not what a tourist is holding, so drink entries exclude them by default.
# "lime" is deliberately absent: Sprite's own product name is "Sprite Lemon Lime Soda",
# so excluding it would reject the standard product.
VARIANTS = r"zero|diet|light|vanilla|cherry|sugar.?free|peach|ginger|apple"


# Entries are brand-specific on purpose. A generic "water 600ml" baseline taken from the
# cheapest local brand makes an Aquafina look overcharged when it is fairly priced, so
# each entry pins one brand at one size -- matching the photo the tourist is holding.
CATALOGUE = [
    # --- Water ---
    # Aquafina 600ml was dropped: Carrefour delisted it mid-development (only a 250ml
    # sparkling can remains), and it had no packshot either.
    # Carrefour holds no packshot for either Dasani -- only a blue mineral-composition
    # table, which tells a tourist nothing. Better no image than one that looks like a
    # completely different product.
    Item("dasani-600ml", "Dasani 600ml", "داساني ٦٠٠ مل", "water", "dasani water",
         r"dasani", (500, 700), 40, ["dasani", "water", "bottle", "small water"],
         image_url="-"),
    Item("dasani-15l", "Dasani 1.5L", "داساني ١.٥ لتر", "water", "dasani water 1.5 liter",
         r"dasani", (1400, 1600), 60, ["dasani", "water", "big water", "large water"],
         image_url="-"),
    Item("aqua-delta-600ml", "Aqua Delta 600ml", "أكوا دلتا ٦٠٠ مل", "water",
         "aqua delta water", r"aqua delta", (500, 700), 40,
         ["water", "cheap water", "local water", "aqua delta", "small water"]),
    # Water is the single most overcharged item, so the common Egyptian brands are all
    # listed individually -- a tourist should find whichever bottle is in their hand
    # rather than having to decide whether it counts as "local water".
    Item("nestle-600ml", "Nestlé Pure Life 600ml", "نستله بيور لايف ٦٠٠ مل", "water",
         "nestle pure life water", r"nestl", (500, 700), 40,
         ["water", "nestle", "pure life", "small water", "bottle"]),
    Item("nestle-1l", "Nestlé Pure Life 1L", "نستله بيور لايف ١ لتر", "water",
         "nestle pure life water 1 liter", r"nestl", (900, 1100), 60,
         ["water", "nestle", "pure life", "big water"]),
    Item("elano-600ml", "Elano 600ml", "إيلانو ٦٠٠ مل", "water", "elano water",
         r"elano", (500, 700), 40, ["water", "elano", "local water", "small water"]),
    Item("elano-15l", "Elano 1.5L", "إيلانو ١.٥ لتر", "water", "elano water 1.5 liter",
         r"elano", (1400, 1600), 60, ["water", "elano", "big water", "large water"]),
    Item("baraka-600ml", "Baraka 600ml", "بركة ٦٠٠ مل", "water", "baraka water",
         r"baraka", (500, 700), 40, ["water", "baraka", "local water", "small water"]),
    Item("baraka-15l", "Baraka 1.5L", "بركة ١.٥ لتر", "water", "baraka water 1.5 liter",
         r"baraka", (1400, 1600), 60, ["water", "baraka", "big water", "large water"]),

    # --- Soft drinks ---
    # A tourist holding a red can means regular Coke, not Vanilla, Zero or an import.
    # Without this, the nearest-size match happily returns "Coca Cola With Vanilla" at
    # 69.50 EGP and every downstream verdict is wrong.
    # Carrefour delisted the plain 300ml can mid-development (only Zero and a 6-pack
    # remain), so the 330ml glass bottle stands in -- the classic Egyptian kiosk Coke.
    Item("coke-glass", "Coca-Cola glass bottle", "كوكاكولا زجاج", "drinks",
         "coca cola glass bottle", r"coca cola.*glass", (320, 340), 60,
         ["coke", "coca cola", "cola", "glass bottle"], exclude=VARIANTS),
    # Carrefour stocks Coke PET only in 950ml and 2.45L online -- there is no 390ml, so
    # the large bottle is the entry rather than inventing a size that is not sold.
    Item("coke-bottle", "Coca-Cola bottle 950ml", "كوكاكولا زجاجة كبيرة", "drinks",
         "coca cola pet bottle", r"coca cola", (900, 1000), 60,
         ["coke", "coca cola", "cola", "bottle", "big coke"],
         exclude=VARIANTS + r"|\bcan\b|glass"),
    Item("pepsi-bottle", "Pepsi bottle", "بيبسي زجاجة", "drinks", "pepsi bottle",
         r"pepsi", (380, 400), 60, ["pepsi", "cola", "soft drink"], exclude=VARIANTS),
    Item("schweppes", "Schweppes 250ml", "شويبس", "drinks", "schweppes",
         r"schweppes", (240, 260), 60,
         ["schweppes", "soda", "tonic", "soft drink", "pomegranate"]),
    # Sprite has no entry: Carrefour now stocks only a 2.45L PET bottle, which is not a
    # kiosk purchase. The 320ml can it sold earlier was delisted, as Aquafina 600ml was.
    # Re-add if the can returns.
    # The 330ml glass bottle rather than the PET: it is the classic Egyptian kiosk
    # purchase, and unlike the PET listing it has a real product photo.
    Item("fanta-glass", "Fanta glass bottle", "فانتا زجاج", "drinks", "fanta can",
         r"fanta.*glass", (320, 340), 60, ["fanta", "orange", "soda", "glass bottle"]),

    # --- Snacks ---
    Item("chipsy", "Chipsy crisps", "شيبسي", "snacks", "chipsy potato chips",
         r"chipsy", (20, 80), 60, ["chipsy", "chips", "crisps", "lays"]),
    Item("doritos", "Doritos", "دوريتوس", "snacks", "doritos",
         r"doritos", (20, 90), 60, ["doritos", "tortilla", "chips", "crisps"]),

    # --- Chocolate. Size window excludes the 22g "wafer roll" variants, which are a
    # different product from the chocolate bar a tourist means. ---
    Item("galaxy-bar", "Galaxy bar", "جالاكسي", "snacks", "galaxy chocolate bar",
         r"galaxy", (30, 120), 80, ["galaxy", "chocolate", "bar"], min_egp=15,
         exclude=r"flute|wafer|biscuit|drink|spread"),
    Item("snickers", "Snickers", "سنيكرز", "snacks", "snickers chocolate",
         r"snickers", (35, 80), 80, ["snickers", "chocolate", "bar"],
         min_egp=15, exclude=r"miniature|minis"),
    Item("kitkat", "KitKat", "كيت كات", "snacks", "kitkat chocolate",
         r"kitkat|kit kat", (30, 120), 80, ["kitkat", "kit kat", "chocolate", "bar"]),

    Item("twix", "Twix", "تويكس", "snacks", "twix chocolate",
         r"twix", (40, 60), 80, ["twix", "chocolate", "bar"],
         exclude=r"roll|mini"),
    Item("bounty", "Bounty", "باونتي", "snacks", "bounty chocolate",
         r"bounty", (40, 60), 80, ["bounty", "coconut", "chocolate", "bar"],
         exclude=r"trio|mini"),
    Item("mars", "Mars bar", "مارس", "snacks", "mars chocolate bar",
         r"\bmars\b", (35, 60), 80, ["mars", "chocolate", "bar"]),
    Item("mms", "M&M's", "إم آند إمز", "snacks", "m&m's chocolate",
         r"m&m", (30, 60), 80, ["m&m", "mms", "chocolate", "candy"], min_egp=15),
    Item("maltesers", "Maltesers", "مالتيزرز", "snacks", "maltesers",
         r"maltesers", (30, 60), 80, ["maltesers", "chocolate", "candy"], min_egp=15),

    # --- Biscuits and cakes. The Egyptian kiosk staples a tourist actually sees on the
    # counter, not just the international brands. ---
    Item("oreo", "Oreo", "أوريو", "snacks", "oreo biscuit",
         r"oreo", None, 40, ["oreo", "biscuit", "cookies"]),
    Item("todo-brownies", "Todo brownies", "تودو براونيز", "snacks", "todo brownies",
         r"todo", None, 60, ["todo", "brownies", "brownie", "cake", "chocolate cake"]),
    Item("molto-croissant", "Molto croissant", "مولتو كرواسون", "snacks",
         "molto croissant", r"molto", None, 60,
         ["molto", "croissant", "chocolate croissant", "pastry"]),
    Item("hohos", "Hohos cake roll", "هوهوز", "snacks", "hohos cake",
         r"hohos", None, 60, ["hohos", "cake", "swiss roll", "chocolate roll"]),
    Item("twinkies", "Twinkies cake", "تwinكيز", "snacks", "twinkies cake",
         r"twinkies", None, 60, ["twinkies", "cake", "cream cake", "sponge"]),
    Item("wafer", "Mandolin wafer", "ويفر ماندولين", "snacks", "mandolin wafer",
         r"mandolin", (20, 60), 40, ["wafer", "waffer", "biscuit", "mandolin"]),
    Item("pringles", "Pringles", "برينجلز", "snacks", "pringles",
         r"pringles", (30, 60), 90, ["pringles", "chips", "crisps"]),

    # --- Juice and milk, sold chilled at every kiosk ---
    Item("juhayna-juice", "Juhayna juice 235ml", "عصير جهينة", "drinks",
         "juhayna juice 235", r"juhayna", (220, 260), 60,
         ["juice", "juhayna", "orange juice", "mango", "guava"]),
    Item("juhayna-milk-1l", "Juhayna milk 1L", "لبن جهينة ١ لتر", "drinks",
         "juhayna milk 1 liter", r"juhayna.*milk|milk.*juhayna", (900, 1100), 90,
         ["milk", "juhayna", "full cream", "laban"]),
    Item("flavoured-milk", "Flavoured milk 190ml", "لبن بنكهة", "drinks",
         "danone dango milk", r"milk", (180, 250), 60,
         ["milk", "chocolate milk", "banana milk", "danone", "dango"]),

    # --- Other ---
    Item("chewing-gum", "Mentos gum", "لبان منتوس", "snacks", "mentos gum",
         r"mentos", (5, 30), 40, ["gum", "chewing gum", "mentos"]),
    Item("extra-gum", "Extra gum", "لبان إكسترا", "snacks", "wrigley extra gum",
         r"extra", (5, 30), 40, ["gum", "chewing gum", "extra", "wrigley"]),
    Item("sting", "Sting energy drink", "ستينج", "drinks", "sting energy drink",
         r"sting", (240, 420), 60, ["sting", "energy", "energy drink"]),
    Item("wet-wipes", "Wet wipes", "مناديل مبللة", "toiletries", "wet wipes pack",
         r"wipes", None, 80, ["wipes", "wet wipes", "baby wipes", "tissues"]),
    Item("redbull", "Red Bull", "ريد بول", "drinks", "red bull energy drink",
         r"red bull", (240, 360), 120, ["red bull", "energy", "energy drink"],
         exclude=VARIANTS),
    # Sunscreen really does cost this much in Egypt -- the cheapest Carrefour stocks is
    # ~190 EGP and the range runs to 380. The high ceiling is correct, not a loose filter.
    Item("sunscreen", "Sunscreen SPF 50", "واقي شمس", "toiletries", "sunscreen spf",
         r"sun(?:screen|block)|spf", (80, 250), 600,
         ["sunscreen", "sunblock", "spf", "sun cream", "nivea"],
         min_egp=50, exclude=r"hair|shampoo|after ?sun"),
    # Sold as a strip of ten packs; the unit a tourist buys is one pack, hence max_pack=12.
    Item("tissues", "Pocket tissues", "مناديل جيب", "toiletries", "pocket tissues",
         r"pocket tissue", None, 20, ["tissues", "kleenex", "napkins"], max_pack=12),
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
        if p.pack_count > item.max_pack:
            continue
        if not (item.min_egp <= p.unit_price_egp <= item.max_egp) or p.unit_price_egp <= 0:
            continue
        if not pattern.search(p.name) or EXCLUDE_RE.search(p.name):
            continue
        if item.exclude and re.search(item.exclude, p.name, re.I):
            continue
        if item.size_range:
            value = size_value(p.size)
            if value is None or not (item.size_range[0] <= value <= item.size_range[1]):
                continue
        candidates.append(p)
    return min(candidates, key=lambda p: p.unit_price_egp) if candidates else None


def _extension_for(body: bytes) -> str:
    """File extension implied by the magic bytes, so the name never lies about the format."""
    if body.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return ".webp"
    if body[4:8] == b"ftyp":  # ISO base media: AVIF/HEIF
        return ".avif"
    return ""


def packshot_score(body: bytes) -> float:
    """How much an image looks like a product shot rather than an information panel.

    Carrefour's photo numbering is unreliable -- for Aquafina and Dasani the first image
    is a mineral-composition table, and for Fanta a barcode strip. Those are useless for
    recognising the bottle in your hand.

    Product shots are cut out on a white studio background, so their border pixels are
    near-white; tables and labels are solid colour to the edge. Scoring the border
    separates them without needing to understand the image.
    """
    try:
        from PIL import Image
    except ImportError:
        return 0.5  # Pillow unavailable: accept whatever came first

    with Image.open(io.BytesIO(body)) as im:
        im = im.convert("RGB")
        width, height = im.size
        if not width or not height:
            return 0.0
        pixels = im.load()
        step = max(1, min(width, height) // 40)
        edge, white = 0, 0
        for x in range(0, width, step):
            for y in (0, height - 1):
                r, g, b = pixels[x, y]
                edge += 1
                white += min(r, g, b) > 235
        for y in range(0, height, step):
            for x in (0, width - 1):
                r, g, b = pixels[x, y]
                edge += 1
                white += min(r, g, b) > 235
    return white / edge if edge else 0.0


def save_image(item_id: str, product: Product, session, image_url: str = "") -> str:
    """Download the product photo into public/ and return its site-relative path.

    Images are committed rather than hotlinked from Carrefour's CDN: a third-party
    request would break the offline mode the whole app depends on, and would leave the
    site's appearance at the mercy of someone else's URL structure.
    """
    if image_url == "-":
        return ""  # curated: Carrefour has no usable packshot for this product
    try:
        urls = [image_url] if image_url else fetch_image_urls(product, session)[:4]
        best: tuple[float, bytes, str] | None = None
        for url in urls:
            # Carrefour's CDN content-negotiates on Accept. Impersonating Chrome advertises
            # AVIF, which silently yields AVIF bytes we would then save under a .jpg name.
            # Ask for JPEG explicitly so the extension matches the content.
            response = session.get(
                url, timeout=45, headers={"Accept": "image/jpeg,image/png"}
            )
            if not response.ok:
                continue
            body = response.content
            if not body or len(body) < 500:
                continue  # placeholder or error page rather than a real photo
            suffix = _extension_for(body)
            if not suffix:
                continue
            score = packshot_score(body)
            if best is None or score > best[0]:
                best = (score, body, suffix)
            if score >= 0.9:
                break  # clean packshot; no need to look at the rest

        if best is None:
            return ""
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        (IMAGE_DIR / f"{item_id}{best[2]}").write_bytes(best[1])
        return f"/products/{item_id}{best[2]}"
    except Exception as exc:  # noqa: BLE001 - a missing photo must not fail the seed
        print(f"     (no image for {item_id}: {exc})", file=sys.stderr)
        return ""


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
        # A link a tourist cannot buy from is not verifiable, so step down to the next
        # cheapest candidate when the best one turns out to be unavailable.
        rejected = []
        while chosen and not is_in_stock(chosen, session):
            print(f"     (out of stock, skipping: {chosen.name[:44]})", file=sys.stderr)
            rejected.append(chosen.product_id)
            chosen = pick([p for p in results if p.product_id not in rejected], item)

        if not chosen:
            print(
                f"  !! {item.id}: no in-stock match among {len(results)} results",
                file=sys.stderr,
            )
            continue

        entries.append({
            "id": item.id,
            "name": item.name,
            "name_ar": item.name_ar,
            "category": item.category,
            "baseline_egp": chosen.unit_price_egp,
            "image": save_image(item.id, chosen, session, item.image_url),
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

    # The offline precache manifest is generated from the real build output by
    # scripts/gen-precache.mjs, since asset filenames are content-hashed at build time.
    return 0 if entries else 1


if __name__ == "__main__":
    raise SystemExit(main())
