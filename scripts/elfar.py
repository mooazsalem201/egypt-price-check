"""Mahmoud El Far scraper, used as a third verification source.

El Far exposes no working search endpoint, so unlike Carrefour and Spinneys it cannot be
queried per product. Instead the handful of categories our catalogue touches are crawled
once, cached in-process, and matched against by keyword.

Its catalogue is client-rendered (a plain fetch returns a 14KB shell with empty
pageProps), so Playwright is required. Product links carry the EAN barcode as a URL
suffix, which is useful for future lookups.

robots.txt permits this: "User-agent: * / Allow: /" with
"Content-Signal: search=yes, ai-train=no, use=reference" -- a price reference is exactly
the declared "use=reference" case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BASE = "https://mahmoudelfar.com"
CATEGORY = BASE + "/en/category/{slug}?currentPage={page}"
# A category page renders 15 items, and Beverages alone holds 441. Two pages per category
# is a deliberate compromise: enough to catch the mainstream brands a tourist buys without
# crawling thousands of listings for a source that only supplies verification links.
PAGES_PER_CATEGORY = 2

# Only the categories our catalogue draws from; crawling all 302 would be wasteful.
CATEGORIES = [
    "water", "mineral-water", "soft-drinks", "energy-drinks", "juice",
    "chips", "snacks", "chocolates", "biscuits-crackers", "cookies-biscuits",
    "tissues", "facial-tissues", "sunscreens-and-tanning-oils",
]

PRICE_RE = re.compile(r"([\d,]+\.\d{2})\s*EGP")
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg|gm)\b", re.I)
# Cards read "6.00 piece | Name 330 Ml Pack 6 Pieces | 356.00 EGP".
PACK_RE = re.compile(r"Pack\s+(\d+)\s+Pieces|(\d+)\s+(?:Pieces|Sachects|Sachets)\b", re.I)
BARCODE_RE = re.compile(r"-(\d{8,14})$")

_cache: dict[str, list["ElFarProduct"]] = {}


@dataclass
class ElFarProduct:
    name: str
    price_egp: float
    size: str
    pack_count: int = 1
    url: str = ""
    barcode: str = ""

    @property
    def unit_price_egp(self) -> float:
        return round(self.price_egp / self.pack_count, 2)


def _scrape_category(slug: str, browser_instance, page_no: int = 1, timeout_ms: int = 45000):
    page = browser_instance.new_page()
    try:
        page.goto(CATEGORY.format(slug=slug, page=page_no), wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(3500)
        # Product anchors carry no text of their own, so walk up to the card that does.
        rows = page.evaluate(
            """() => {
              const out = [], seen = new Set();
              document.querySelectorAll('a[href^="/products/"]').forEach(a => {
                const href = a.getAttribute('href');
                if (seen.has(href)) return;
                let el = a, text = '';
                for (let i = 0; i < 5 && el; i++) {
                  el = el.parentElement;
                  if (el && /EGP/.test(el.innerText || '')) {
                    text = el.innerText.trim().replace(/\\n+/g, ' | ');
                    break;
                  }
                }
                if (text) { seen.add(href); out.push({ text, href }); }
              });
              return out;
            }"""
        )
    except Exception:
        return []
    finally:
        page.close()

    products = []
    for row in rows:
        text, href = row["text"], row["href"]
        prices = PRICE_RE.findall(text)
        if not prices:
            continue
        # Strip the leading unit-size chip and the trailing price to leave the name.
        parts = [p.strip() for p in text.split("|") if p.strip()]
        name_parts = [p for p in parts if not PRICE_RE.search(p) and not re.match(r"^[\d.]+\s*(piece|ml|g|kg|l)s?$", p, re.I)]
        name = " ".join(name_parts).strip()
        if not name:
            continue
        # El Far prefixes unavailable items with their status, which would otherwise end
        # up in the product name and, worse, be offered as a price reference for something
        # nobody can buy.
        if re.match(r"^\s*out of stock\b", name, re.I):
            continue
        pack_match = PACK_RE.search(name)
        pack = int(next(g for g in pack_match.groups() if g)) if pack_match else 1
        size = SIZE_RE.search(name)
        barcode = BARCODE_RE.search(href)
        products.append(
            ElFarProduct(
                name=name,
                price_egp=float(prices[-1].replace(",", "")),
                size=size.group(0).lower() if size else "",
                pack_count=max(1, pack),
                url=BASE + href,
                barcode=barcode.group(1) if barcode else "",
            )
        )
    return products


def search(keyword: str, browser_instance) -> list[ElFarProduct]:
    """Products matching a keyword, crawling the relevant categories once per process."""
    if not _cache:
        for slug in CATEGORIES:
            items = []
            for page_no in range(1, PAGES_PER_CATEGORY + 1):
                items.extend(_scrape_category(slug, browser_instance, page_no))
            _cache[slug] = items

    everything = [p for items in _cache.values() for p in items]
    tokens = [t for t in re.split(r"\W+", keyword.lower()) if len(t) > 2]
    if not tokens:
        return everything
    # Whole words only: a substring match makes "cola" hit "cho-cola-te", which then wins
    # the price comparison and reports a nonsense disagreement.
    patterns = [re.compile(rf"\b{re.escape(t)}\b", re.I) for t in tokens]
    return [p for p in everything if any(pat.search(p.name) for pat in patterns)]
