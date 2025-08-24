
import argparse, json, sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from .connector import crawl_listing, parse_product
from .normalize import choose_brand
from . import storage

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to site config JSON")
    ap.add_argument("--db", default="um.db", help="SQLite DB path")
    ap.add_argument("--export-json", default="out/products.json", help="Export JSON path")
    ap.add_argument("--brands-seed", default="config/brands_seed.json", help="Brands seed")
    ap.add_argument("--brand-aliases", default="config/brand_aliases.json", help="Brand aliases")
    args = ap.parse_args()

    conf = load_json(args.config)
    aliases = load_json(args.brand_aliases) if Path(args.brand_aliases).exists() else []
    brands_seed = load_json(args.brands_seed) if Path(args.brands_seed).exists() else []

    conn = storage.init_db(args.db)
    if brands_seed:
        storage.seed_brands(conn, brands_seed)
    if aliases:
        storage.upsert_brand_aliases(conn, aliases)

    start_urls = conf["listing"]["start_urls"]
    product_link_sel = conf["listing"]["product_link_selector"]
    pagination_sel = conf["listing"].get("pagination_next_selector")
    product_conf = conf["product_page"]
    force_brand = conf.get("routing", {}).get("force_brand_for_domain")
    threshold = float(conf.get("routing", {}).get("confidence_threshold") or 0.8)

    imported = 0
    for u in start_urls:
        product_urls = crawl_listing(u, product_link_sel, pagination_sel)
        for pu in product_urls:
            try:
                p = parse_product(pu, product_conf)

                # Brand resolution
                brand_name, confidence = (force_brand, 1.0) if force_brand else (None, 0.0)
                if not brand_name:
                    brand_name, confidence = choose_brand(p.get("brand_raw"), p.get("title"), aliases, None)

                brand_id = None
                if brand_name and confidence >= threshold:
                    # ensure brand + collection
                    _cid = storage.get_or_create_brand_collection(conn, brand_name)
                    brand_id = conn.execute("SELECT id FROM brands WHERE name=?", (brand_name,)).fetchone()[0]

                prod_id = storage.upsert_product(conn, {
                    "source": conf["source"],
                    "url": p["url"],
                    "title": p.get("title"),
                    "brand_id": brand_id,
                    "sku": p.get("sku"),
                    "gtin": p.get("gtin"),
                    "description_html": p.get("description_html"),
                    "currency": p.get("currency"),
                    "price": p.get("price"),
                    "stock_status": p.get("stock_status"),
                    "category_path": p.get("category_path")
                })

                storage.replace_media(conn, prod_id, p.get("images"))

                if brand_id:
                    brand = conn.execute("SELECT name FROM brands WHERE id=?", (brand_id,)).fetchone()[0]
                    cid = storage.get_or_create_brand_collection(conn, brand)
                    storage.attach_to_collection(conn, cid, prod_id)

                imported += 1
            except Exception as e:
                print(f"[ERROR] {pu}: {e}", file=sys.stderr)
                continue

    storage.export_products_json(conn, args.export_json)
    print(f"Imported {imported} products. Exported JSON: {args.export_json}")

if __name__ == "__main__":
    main()
