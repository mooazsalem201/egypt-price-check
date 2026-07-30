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
# Capture the whole href, query string included. Carrefour is a marketplace: the same
# product id is sold by several sellers, and "?offer=offer_carrefour_&sellerId=0000" is
# what pins the link to Carrefour's own in-stock offer. Truncating at the id sends users
# to whichever seller the site defaults to, which is often out of stock.
PRODUCT_HREF_RE = re.compile(r'href="(/mafegy/en/[^"]*?/p/(\d+)[^"]*)"')

# Pairing by filename prefix is the only reliable way to link an image to a product on a
# listing page, because the <img> sits before the product link in the DOM and so falls
# outside the tile split.
#
# Carrefour serves product photos from two path roots (sys-master-root and pim-content)
# and with two filename shapes ("{id}_main" and "{id}_2"). Handling only some combinations
# silently produced imageless products -- Todo brownies, Maltesers, Sting and wet wipes all
# used sys-master-root/..._main, which matched neither of the original patterns.
IMAGE_RE = re.compile(
    r"https://cdn\.mafrservices\.com/(?:sys-master-root|pim-content)/[^\"\s\\]+?"
    r"/(\d+)_(?:main|\d+)\.(?:jpg|jpeg|png|webp)[^\"\s\\]*"
)
# "_main" is the canonical packshot wherever it appears, so it is preferred.
MAIN_IMAGE_RE = re.compile(
    r"https://cdn\.mafrservices\.com/(?:sys-master-root|pim-content)/[^\"\s\\]+?"
    r"_main\.(?:jpg|jpeg|png|webp)[^\"\s\\]*"
)
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
    image_url: str = ""

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
        # Carrefour also repeats non-size units ("... - 1 Piece 1 Piece"), which the size
        # cut above does not catch. Collapse any immediately repeated trailing phrase.
        name = re.sub(r"\b(.{3,20}?)\s+\1\s*$", r"\1", name, flags=re.I)
        # Tidy a dash or comma left dangling by the cut.
        return re.sub(r"\s*[-–,]\s*$", "", name)
    return slug.replace("-", " ").title()


def _image_map(html: str) -> dict[str, str]:
    """Map product id -> first CDN image URL, taken across the whole page."""
    images: dict[str, str] = {}
    for match in IMAGE_RE.finditer(html):
        images.setdefault(match.group(1), match.group(0).rstrip("\\"))
    return images


def parse_search_html(html: str) -> list[Product]:
    """Parse a rendered Carrefour search page into products with per-unit prices."""
    products: list[Product] = []
    seen: set[str] = set()
    images = _image_map(html)

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
                image_url=images.get(product_id, ""),
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


# Product pages are fetched for both the photo and the stock check; caching avoids
# requesting the same page twice per item.
_page_cache: dict[str, str] = {}

OUT_OF_STOCK_RE = re.compile(r"out of stock|sold out|غير متوفر", re.I)


def _product_page(url: str, session: requests.Session) -> str:
    if url not in _page_cache:
        _page_cache[url] = session.get(url, timeout=45).text
    return _page_cache[url]


def is_in_stock(product: Product, session: requests.Session) -> bool:
    """Whether the product page still offers the item.

    Search results are generally in stock, but a listing can go unavailable between the
    search and the link a tourist eventually taps. A baseline pointing at something that
    cannot be bought is not verifiable, which is the whole point of publishing the link.
    """
    page = _product_page(product.url, session)
    # An orderable page renders an "Add to cart" control; an unavailable one does not.
    # The out-of-stock phrase alone is unreliable because it also appears in the
    # "you might also like" tiles of a perfectly available product.
    if "add to cart" not in page.lower():
        return False
    return len(OUT_OF_STOCK_RE.findall(page)) < 6


def _image_suffix(url: str) -> int:
    """The "_N" index of a CDN photo; lower means the primary packaging shot."""
    match = re.search(r"_(\d+)\.(?:jpg|jpeg|png|webp)", url)
    return int(match.group(1)) if match else 99


def fetch_image_url(product: Product, session: requests.Session, width: int = 400) -> str:
    """Best image URL for a product, fetching its detail page if the listing lacked one.

    Listing pages lazy-load images, so only the products above the fold carry a real
    `src`. The detail page always has the canonical `_main` photo.
    """
    urls = fetch_image_urls(product, session, width)
    return urls[0] if urls else ""


def fetch_image_urls(
    product: Product, session: requests.Session, width: int = 400
) -> list[str]:
    """All candidate photo URLs for a product, best-guess first.

    A product carries several shots and the numbering is not dependable: for some items
    "_1" is the packaging, for others (Aquafina, Dasani) it is a mineral-composition table
    that tells a tourist nothing. Callers pick between them by inspecting the images.
    """
    page = _product_page(product.url, session)

    candidates = [m.group(0).rstrip("\\") for m in MAIN_IMAGE_RE.finditer(page)]
    candidates += sorted(
        {m.group(0).rstrip("\\") for m in IMAGE_RE.finditer(page)}, key=_image_suffix
    )
    if product.image_url:
        candidates.append(product.image_url)

    seen: set[str] = set()
    out: list[str] = []
    for url in candidates:
        # The CDN resizes server-side; ask for the display size, not a 2MB original.
        sized = re.sub(r"\?im=Resize=\d+", "", url) + f"?im=Resize={width}"
        if sized not in seen:
            seen.add(sized)
            out.append(sized)
    return out
