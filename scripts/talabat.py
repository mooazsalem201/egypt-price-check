"""Talabat Mart scraper.

Talabat is geo-gated at the top level: the country and vertical landing pages carry only
CMS content, and its internal vendor APIs return 404/503 without a location. But a direct
store URL sidesteps all of that, and the page is server-rendered -- products sit in
__NEXT_DATA__ under initialState.itemsData.items, so curl_cffi is enough and no browser
is needed.

Worth having despite three other sources: Talabat Mart is a convenience/delivery service
rather than a hypermarket, so its prices sit between a supermarket shelf and a street
kiosk -- closer to what a tourist actually pays than Carrefour is.

URLs look like:
    /egypt/grocery/{branch_id}/{branch_slug}/{parent}/{child}?aid={area_id}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from curl_cffi import requests

BASE = "https://www.talabat.com"
IMPERSONATE = "chrome124"

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg|gm|gram|liters?|litres?)\b", re.I)
# "12 Pcs", "Pack of 6", "x24" -- a case, not a single item.
PACK_RE = re.compile(r"(\d{1,3})\s*(?:pcs|pieces|pack)\b|pack of (\d{1,3})|x\s*(\d{1,3})\b", re.I)


@dataclass(frozen=True)
class Store:
    branch_id: str
    branch_slug: str
    area_id: int
    label: str

    def category_url(self, parent: str, child: str) -> str:
        return (
            f"{BASE}/egypt/grocery/{self.branch_id}/{self.branch_slug}"
            f"/{parent}/{child}?aid={self.area_id}"
        )


# The store the working URL pointed at. Talabat Mart prices are set per store, so adding
# more branches here would allow the same regional comparison Seoudi supports.
EL_SUEZ = Store("801350", "talabat-mart-el-suez", 6963, "Talabat Mart (El Suez)")


@dataclass
class TalabatProduct:
    name: str
    price_egp: float
    size: str
    pack_count: int
    url: str
    slug: str

    @property
    def unit_price_egp(self) -> float:
        return round(self.price_egp / self.pack_count, 2)


def new_session() -> requests.Session:
    return requests.Session(impersonate=IMPERSONATE)


def scrape_category(
    parent: str, child: str, store: Store = EL_SUEZ, session: requests.Session | None = None
) -> list[TalabatProduct]:
    """Products in one Talabat Mart category."""
    session = session or new_session()
    url = store.category_url(parent, child)
    response = session.get(url, timeout=45)
    response.raise_for_status()

    match = NEXT_DATA_RE.search(response.text)
    if not match:
        raise RuntimeError(f"no __NEXT_DATA__ at {url}")
    state = json.loads(match.group(1))["props"]["pageProps"]["initialState"]
    items = state.get("itemsData", {}).get("items", []) or []

    products: list[TalabatProduct] = []
    # Talabat has no per-product pages -- items open in an overlay on the category page,
    # and the raw HTML carries category hrefs only. Guessing a /{slug} URL yields a 404.
    # The category page is therefore the honest link: it is live, it is the page the price
    # was actually read from, and the product is on it.
    for item in items:
        title = (item.get("title") or "").strip()
        price = item.get("price")
        if not title or not isinstance(price, (int, float)) or price <= 0:
            continue
        pack_match = PACK_RE.search(title)
        pack = int(next(g for g in pack_match.groups() if g)) if pack_match else 1
        size = SIZE_RE.search(title)
        slug = item.get("slug", "")
        products.append(
            TalabatProduct(
                name=title,
                price_egp=float(price),
                size=size.group(0).lower() if size else "",
                pack_count=max(1, pack),
                url=url,
                slug=slug,
            )
        )
    return products


# Categories the tourist catalogue draws from, as (parent, child) pairs.
CATEGORIES = [
    ("beverages", "water"),
    ("beverages", "soft-drinks"),
    ("beverages", "juices"),
    ("beverages", "sports-energy-drinks"),
    ("snacks-chocolate", "chocolate"),
    ("snacks-chocolate", "biscuits"),
    ("snacks-chocolate", "cakes"),
    ("snacks-chocolate", "chips-dips"),
    ("snacks-chocolate", "candy-gums"),
    ("dairy-eggs", "chilled-desserts"),
]

_cache: dict[str, list[TalabatProduct]] = {}


def search(keyword: str, session: requests.Session | None = None) -> list[TalabatProduct]:
    """Products matching a keyword, crawling the relevant categories once per process."""
    session = session or new_session()
    if not _cache:
        for parent, child in CATEGORIES:
            try:
                _cache[f"{parent}/{child}"] = scrape_category(parent, child, session=session)
            except Exception:  # noqa: BLE001 - one dead category must not stop the sweep
                _cache[f"{parent}/{child}"] = []

    everything = [p for items in _cache.values() for p in items]
    tokens = [t for t in re.split(r"\W+", keyword.lower()) if len(t) > 2]
    if not tokens:
        return everything
    # Whole words only -- substring matching makes "cola" hit "chocolate".
    patterns = [re.compile(rf"\b{re.escape(t)}\b", re.I) for t in tokens]
    return [p for p in everything if any(pat.search(p.name) for pat in patterns)]
