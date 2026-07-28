# Egypt Price Check

A static website that tells tourists what everyday items should cost in Egypt, adjusted
for where in the country they are, shown in their own currency. Works offline.

Search a product → see the fair price range for your area → optionally type the price
you're being quoted and get a verdict plus a counter-offer.

## Why it is built this way

**No server, no database.** The dataset is ~12 products that change a few times a year.
That is a JSON file, not a backend. `next build` emits static HTML/JS which any CDN
serves for free, so hosting costs nothing and there is nothing to maintain or patch.

**No user input is collected.** The price-check box is browser-side arithmetic; nothing
is sent anywhere. There are no accounts, no analytics, no forms.

**Offline first.** Cell service is unreliable at the pyramids and along the North Coast,
which is exactly where the app is needed. A service worker caches everything, and prices
are baked into the bundle at build time.

## Where the prices come from

Scraped from **Carrefour Egypt**, which sits behind Akamai Bot Manager. Akamai
fingerprints the TLS handshake and HTTP/2 frame ordering, so `requests`, Scrapy, urllib
and plain `curl` all receive a 53-byte empty stub regardless of the headers they send:

```html
<!DOCTYPE html>
<html>
<body>
<p></p>
</body>
</html>
```

BeautifulSoup cannot help — it is a parser, and there is nothing in that response to
parse. The fix is at the transport layer. [`curl_cffi`](https://github.com/lexiforest/curl_cffi)
wraps `curl-impersonate` and reproduces Chrome's exact JA3/TLS fingerprint, which returns
the full ~1.1MB rendered page. Search results are server-rendered, so no browser
automation is needed.

Carrefour sells multipacks, so `scripts/carrefour.py` parses the pack count and derives a
**per-unit** price — a tourist buys one bottle, not a case of twelve.

Two Carrefour quirks worth knowing before editing the scraper:

- **It is a marketplace.** The same product id is sold by several sellers, and the
  `?offer=offer_carrefour_&sellerId=0000` query string is what pins a link to Carrefour's
  own offer. Truncating a product URL at the id sends users to whichever seller the site
  defaults to, which is frequently out of stock.
- **Its catalogue churns.** Aquafina 600ml and the Sprite 320ml can were both delisted
  during development. Each chosen product is stock-checked before being committed, and the
  seeder steps down to the next cheapest candidate when one is unavailable.

## Zone multipliers

`data/zones.json` scales the Cairo baseline by region. Each carries a `source`:

- `measured` — from scraped data (Cairo)
- `reported` — local knowledge from someone who lives there (Sahel)
- `estimate` — a judgement call, and labelled as such in the UI

**Sahel is 1.0, not the 2.0 originally assumed.** Its resort reputation is about bars and
restaurants; packaged goods at kiosks sell at ordinary prices, partly because many
Egyptian packs carry a printed price (سعر الجمهور) that caps what a shop can charge. An
inflated multiplier here was actively harmful: at 2.0 the app would have called 30 EGP for
a 6 EGP bottle "fair".

This was tested rather than assumed: Spinneys Egypt runs a separate `/en/sahel/`
storefront, which looked like a way to measure real North Coast pricing. Comparing all 12
matched products between the Sahel and main catalogues gave a price ratio of **1.000 for
every one** — Egyptian online grocers price nationally, and the Sahel section is a curated
category, not a regional price list. Kiosk and resort markups are not observable from any
grocery website.

The UI labels estimated zones as such rather than presenting them as fact. Tune the
numbers in `data/zones.json` against local knowledge.

## Development

```bash
npm install
npm run dev                 # http://localhost:3000
npm test                    # pricing logic unit tests
npm run build               # static export to out/
```

Scraper (Python 3.12+):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/seed_products.py     # rewrite data/products.json
.venv/bin/python scripts/refresh.py --check   # report drift, write nothing
```

## Weekly refresh

`.github/workflows/refresh-prices.yml` re-checks prices every Monday and opens an issue
when anything moved more than 10%. It deliberately **does not** rewrite prices
automatically: a scrape failure or a Carrefour redesign must never silently poison the
baselines. CI reports; a human merges.

If the scraper breaks entirely, the site keeps working on the last committed data.

## Layout

```
app/page.tsx              single page
components/PriceChecker   search, zone + currency pickers
components/ProductCard    price bands and the local price check
lib/pricing.ts            fair/high/overcharged maths  (unit-tested)
lib/currency.ts           FX with cache and offline fallback
data/products.json        baselines, with a source URL per item
data/zones.json           regional multipliers + provenance
scripts/carrefour.py      Akamai-bypassing scraper
scripts/seed_products.py  builds products.json
scripts/refresh.py        weekly drift report
```

## Deploying

Any static host. Vercel and Cloudflare Pages both work on the free tier:

```bash
npm run build     # output lands in out/
```

## Known limitations

- Supermarket prices are a **baseline**, not kiosk prices; the kiosk markup bands are
  estimates.
- Only Cairo is measured and Sahel reported; Giza, Luxor and the Red Sea remain estimates.
- Baselines go stale with inflation — hence the weekly check and the visible
  "verified" date on each card.
- Carrefour's search is loose (querying "water 1.5 liter" returns water *heaters*), so
  `scripts/seed_products.py` constrains every item by name pattern, size window and a
  price ceiling. New catalogue entries need the same care.
