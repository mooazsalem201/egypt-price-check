"""Re-fetch photos for products that are missing one, without re-seeding everything.

A full seed runs a search per catalogue entry and is heavy enough that Carrefour starts
timing out under it. When only the images need repairing, the product URLs are already
committed -- one page fetch each is enough, and nothing else in data/products.json is
touched.

    .venv/bin/python scripts/fix_images.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from carrefour import Product, new_session  # noqa: E402
from seed_products import CATALOGUE, OUT, save_image  # noqa: E402


def main() -> int:
    products = json.loads(OUT.read_text(encoding="utf-8"))
    catalogue = {item.id: item for item in CATALOGUE}
    fixed = 0

    for entry in products:
        if entry.get("image"):
            continue
        item = catalogue.get(entry["id"])
        # "-" means a human decided Carrefour has no usable packshot; leave it alone.
        if item is None or item.image_url == "-":
            print(f"  {entry['id']:16} skipped (curated as having no usable photo)")
            continue

        stub = Product(
            product_id="",
            name=entry["source"]["product"],
            url=entry["source"]["url"],
            price_egp=0,
            pack_count=1,
            unit_price_egp=0,
            size=entry["source"].get("size", ""),
        )
        path = save_image(entry["id"], stub, new_session(), item.image_url)
        entry["image"] = path
        fixed += bool(path)
        print(f"  {entry['id']:16} {'-> ' + path if path else 'still no image'}")

    OUT.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nrepaired {fixed} image(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
