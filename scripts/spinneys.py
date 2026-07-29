"""Spinneys Egypt scraper, used to cross-check Carrefour prices.

Spinneys has no bot protection, and robots.txt permits crawling, but its catalogue is
rendered client-side -- a plain HTTP fetch of a category page returns a 364KB document
containing zero "EGP" strings. A real browser is required, so this uses Playwright while
the Carrefour scraper can stay on lightweight HTTP.

The point is validation rather than averaging. Chains genuinely price differently, so a
mean across them would blur the baseline; but if two independent stores disagree wildly on
the same product, the likelier explanation is a parsing bug than a real 3x price gap.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass

SEARCH = "https://spinneys-egypt.com/en/search?q={kw}"

# Result rows read "COCA COLA - 355ML | 16.50 EGP" once innerText is normalised. Discounted
# items carry two prices ("... | 60.00 EGP | 71.50 EGP"), so the name is everything before
# the FIRST price and the amount charged is the LAST one.
PRICE_RE = re.compile(r"([\d,]+\.\d{2})\s*EGP")
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg|gm)\b", re.I)
# Multipacks appear as "12 * 600ml", "- 9PC", "6 X 250ML". Without dividing these out a
# 12-pack of water reads as a single bottle costing 60 EGP.
PACK_RE = re.compile(
    r"(?:^|[\s\-])(\d{1,2})\s*(?:\*|x|X)\s*\d|(\d{1,2})\s*PC\b",
    re.I,
)
# "DUO", "TRIO" and similar name a multipack without a digit anywhere.
NAMED_PACK_RE = re.compile(r"\b(duo|trio|twin|multipack|family pack)\b", re.I)


BASE = "https://spinneys-egypt.com"


@dataclass
class SpinneysProduct:
    name: str
    price_egp: float
    size: str
    pack_count: int = 1
    url: str = ""

    @property
    def unit_price_egp(self) -> float:
        return round(self.price_egp / self.pack_count, 2)


@contextmanager
def browser():
    """Playwright browser context. Kept separate so callers can reuse one instance."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        instance = p.chromium.launch()
        try:
            yield instance
        finally:
            instance.close()


def search(keyword: str, browser_instance, timeout_ms: int = 45000) -> list[SpinneysProduct]:
    """Search Spinneys and return the rendered result rows."""
    page = browser_instance.new_page()
    try:
        page.goto(SEARCH.format(kw=keyword.replace(" ", "%20")),
                  wait_until="networkidle", timeout=timeout_ms)
        # The grid populates after hydration; innerText is empty without this settle time.
        page.wait_for_timeout(3000)
        # Keep the href alongside the text: the app links back to the source listing so a
        # tourist (or a maintainer) can verify a price rather than take it on faith.
        rows = page.evaluate(
            """() => Array.from(document.querySelectorAll('a'))
                 .map(a => ({
                   text: (a.innerText || '').trim().replace(/\\n+/g, ' | '),
                   href: a.getAttribute('href') || ''
                 }))
                 .filter(r => /EGP/.test(r.text) && r.text.length < 200)"""
        )
    finally:
        page.close()

    products: list[SpinneysProduct] = []
    seen: set[str] = set()
    for entry in rows:
        row, href = entry["text"], entry["href"]
        prices = PRICE_RE.findall(row)
        if not prices:
            continue
        # Name is what precedes the first price; the charged amount is the last one.
        name = re.sub(r"\s+", " ", row[: PRICE_RE.search(row).start()]).strip(" |-")
        if not name or name in seen:
            continue
        seen.add(name)

        size = SIZE_RE.search(name)
        pack_match = PACK_RE.search(name)
        pack = int(next(g for g in pack_match.groups() if g)) if pack_match else 1
        if pack == 1 and NAMED_PACK_RE.search(name):
            pack = 2  # unknown count, but definitely more than one
        products.append(
            SpinneysProduct(
                name=name,
                price_egp=float(prices[-1].replace(",", "")),
                size=size.group(0).lower() if size else "",
                pack_count=max(1, pack),
                url=(BASE + href) if href.startswith("/") else href,
            )
        )
    return products
