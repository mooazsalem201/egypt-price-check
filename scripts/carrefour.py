"""Carrefour Egypt scraper.

Carrefour sits behind Akamai Bot Manager, which fingerprints the TLS handshake and
HTTP/2 frame ordering. Any ordinary Python HTTP client (requests, Scrapy, urllib) and
plain curl receive a 53-byte empty stub:

    <!DOCTYPE html>\\n<html>\\n<body>\\n<p></p>\\n</body>\\n</html>

BeautifulSoup cannot help with that -- it is a parser, and there is nothing to parse.
The fix is at the transport layer: curl_cffi wraps curl-impersonate and reproduces
Chrome's exact JA3/TLS fingerprint, which returns the full ~1.1MB rendered page.

Search results are server-rendered, so no browser automation is needed here.
"""

from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass, asdict

from curl_cffi import requests

BASE = "https://www.carrefouregypt.com"
SEARCH = BASE + "/mafegy/en/search?keyword={kw}"
IMPERSONATE = "chrome124"

# Prices are rendered across separate DOM elements -- "107", ".", "50", "EGP" -- so
# after tag-stripping the text reads "107 . 50 EGP". The integer part must not absorb
# spaces, or an adjacent pack count ("12 Pieces 107 . 50") merges into "12107.50".
PRICE_RE = re.compile(r"(?<!\d)(\d{1,5})\s*\.\s*(\d{2})\s*EGP")
PRODUCT_SPLIT_RE = re.compile(r'(?=href="/mafegy/en/[^"]*?/p/\d+)')
PRODUCT_HREF_RE = re.compile(r'href="(/mafegy/en/[^"]*?/p/(\d+))')
# Multipacks are labelled several ways: "x Pack of 12", "- 12 Pieces", "- 20 Bottles".
# Missing one makes a 12-pack look like a single item and understates the unit price.
PACK_RE = re.compile(
    r"Pack of (\d+)|(?<!\d)(\d{1,3})\s*(?:Pieces|Pcs|Bottles|Cans|Sachets|Rolls)\b",
    re.I,
)
# Sizes appear as "600ml", "1.5L" and spelled out as "1.5 Liter"/"80 Gram". Matching only
# the abbreviations parsed "1.5 Liter" as "5 l", so the long forms are listed explicitly and
# the alternation is ordered longest-first.
SIZE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kilograms?|kg|grams?|gm?|millilitres?|milliliters?|ml|lit(?:re|er)s?|l)(?![a-z])",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass
class Product:
    product_id: str
    name: str
    url: str
    price_egp: float
    pack_count: int
    unit_price_egp: float
    size: str

    def as_dict(self) -> dict:
        return asdict(self)


def _clean(fragment: str) -> str:
    """Strip tags and collapse whitespace so split price elements become readable text."""
    return WS_RE.sub(" ", html_mod.unescape(TAG_RE.sub(" ", fragment))).strip()


def _extract_name(text: str, slug: str) -> str:
    """Prefer the rendered display name; fall back to a title-cased URL slug.

    The tile text runs "<name> <size> <size> <price> EGP Tom. 12:00 PM ...", so the
    name is whatever precedes the price. Trimming there avoids dragging the repeated
    size and delivery-slot text into the name.
    """
    head = text[: PRICE_RE.search(text).start()] if PRICE_RE.search(text) else text
    match = re.search(r"([A-Z][\w&'\-]*(?: [\w&'\-.,]+){2,14})", head)
    if match:
        name = match.group(1).strip()
        # Carrefour renders the size twice -- once in the title, once as a separate
        # attribute -- giving "... - 1.5 Liter 1.5 Liter". Cut at the second occurrence.
        sizes = list(SIZE_RE.finditer(name))
        if len(sizes) > 1:
            name = name[: sizes[1].start()].strip()
        # Tidy a dash or comma left dangling by the cut.
        return re.sub(r"\s*[-–,]\s*$", "", name)
    return slug.replace("-", " ").title()


def parse_search_html(html: str) -> list[Product]:
    """Parse a rendered Carrefour search page into products with per-unit prices."""
    products: list[Product] = []
    seen: set[str] = set()

    for tile in PRODUCT_SPLIT_RE.split(html)[1:]:
        href_match = PRODUCT_HREF_RE.match(tile)
        if not href_match:
            continue
        path, product_id = href_match.group(1), href_match.group(2)
        if product_id in seen:
            continue

        text = _clean(tile[:3000])
        price_match = PRICE_RE.search(text)
        if not price_match:
            continue

        seen.add(product_id)
        price = float(f"{price_match.group(1)}.{price_match.group(2)}")
        pack_match = PACK_RE.search(text)
        pack = int(pack_match.group(1) or pack_match.group(2)) if pack_match else 1
        slug = path.split("/p/")[0].rsplit("/", 1)[-1]
        name = _extract_name(text, slug)
        # Read the size from the product name, not the whole tile: badges and delivery
        # copy earlier in the tile otherwise win the match and turn "1.5 Liter" into "5 l".
        size_match = SIZE_RE.search(name) or SIZE_RE.search(text)

        products.append(
            Product(
                product_id=product_id,
                name=name,
                url=BASE + html_mod.unescape(path),
                price_egp=price,
                pack_count=pack,
                # A tourist buys one bottle, not a 12-pack -- the per-unit price is
                # what the app compares a kiosk quote against.
                unit_price_egp=round(price / pack, 2),
                size=size_match.group(0).lower() if size_match else "",
            )
        )

    return products


def search(keyword: str, session: requests.Session | None = None) -> list[Product]:
    """Fetch and parse one Carrefour search query."""
    session = session or requests.Session(impersonate=IMPERSONATE)
    response = session.get(SEARCH.format(kw=keyword), timeout=45)
    response.raise_for_status()
    if len(response.text) < 1000:
        raise RuntimeError(
            f"Carrefour returned a {len(response.text)}-byte stub for {keyword!r}; "
            "the Akamai bypass is no longer working."
        )
    return parse_search_html(response.text)


def new_session() -> requests.Session:
    return requests.Session(impersonate=IMPERSONATE)
