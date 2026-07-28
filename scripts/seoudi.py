"""Seoudi Market scraper — the one source that prices per location.

Seoudi is gated: every URL returns a ~490-byte shell until a city, area and district are
chosen, because the catalogue and its prices are per store. That gate is the reason it
cannot be scraped like the others, and also the reason it is worth the trouble -- Carrefour,
Spinneys and El Far all price nationally, so none of them can answer whether a bottle costs
more in the North Coast than in Cairo. Seoudi can.

robots.txt permits this: "User-agent: * / Allow: /" with
"Content-Signal: search=yes, ai-train=no, use=reference".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BASE = "https://seoudisupermarket.com"
STORE_PICKER = BASE + "/en/select-store"
CATEGORY = BASE + "/en/{slug}"

# Cards render as a name line followed by a price line. Discounted items show the sale
# price first and the old price second, so the FIRST price is what is actually charged.
PRICE_LINE_RE = re.compile(r"^([\d,]+\.\d{2})\s*EGP$")
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg|gm|liters?|litres?)\b", re.I)
PACK_RE = re.compile(r"pack of (\d+)|(\d+)\s*(?:pieces|pcs)\b", re.I)

# Lines that are chrome, not products.
CHROME = {
    "all categories", "home", "deals", "reset", "default", "has deal",
    "available stores", "brand", "price", "on sale", "عربي",
}


@dataclass
class SeoudiProduct:
    name: str
    price_egp: float
    size: str
    pack_count: int = 1
    location: str = ""

    @property
    def unit_price_egp(self) -> float:
        return round(self.price_egp / self.pack_count, 2)


def choose_location(page, city: str, area: str | None = None, district: str | None = None):
    """Pass the store gate. Returns the (area, district) actually selected."""
    page.goto(STORE_PICKER, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    # "#city" matches both a wrapper div and the real control, hence the tag qualifier.
    page.select_option("select#city", label=city)
    page.wait_for_timeout(2200)
    areas = page.evaluate(
        "()=>Array.from(document.querySelector('select#area').options)"
        ".map(o=>o.text.trim()).filter(Boolean)"
    )
    if not areas:
        raise RuntimeError(f"no areas offered for city {city!r}")
    chosen_area = area if area in areas else areas[0]
    page.select_option("select#area", label=chosen_area)
    page.wait_for_timeout(2200)

    districts = page.evaluate(
        "()=>Array.from(document.querySelector('select#district').options)"
        ".map(o=>o.text.trim()).filter(Boolean)"
    )
    chosen_district = None
    if districts:
        chosen_district = district if district in districts else districts[0]
        page.select_option("select#district", label=chosen_district)
        page.wait_for_timeout(1800)

    # The confirm button reports enabled but sits beneath the map overlay, which swallows
    # real pointer events; dispatching the click directly is the only reliable route.
    page.evaluate(
        """() => {
          const b = [...document.querySelectorAll('button')]
            .find(x => /continue to shop/i.test(x.innerText || ''));
          if (b) { b.disabled = false; b.click(); }
        }"""
    )
    page.wait_for_timeout(6000)
    return chosen_area, chosen_district


def scrape_category(page, slug: str, location: str = "") -> list[SeoudiProduct]:
    """Products in one category for whichever store is currently selected."""
    page.goto(CATEGORY.format(slug=slug), wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)
    lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]

    products: list[SeoudiProduct] = []
    for i, line in enumerate(lines):
        match = PRICE_LINE_RE.match(line)
        if not match or i == 0:
            continue
        name = lines[i - 1]
        # The previous line is the name only if it is not itself a price (discounted items
        # stack two price lines) and not part of the page furniture.
        if PRICE_LINE_RE.match(name) or name.lower() in CHROME or len(name) < 4:
            continue
        size = SIZE_RE.search(name)
        pack = PACK_RE.search(name)
        products.append(
            SeoudiProduct(
                name=name,
                price_egp=float(match.group(1).replace(",", "")),
                size=size.group(0).lower() if size else "",
                pack_count=int(next(g for g in pack.groups() if g)) if pack else 1,
                location=location,
            )
        )
    return products
