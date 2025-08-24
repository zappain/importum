
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  slug TEXT UNIQUE,
  status TEXT DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS brand_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id INTEGER NOT NULL,
  alias TEXT NOT NULL,
  priority INTEGER DEFAULT 1,
  UNIQUE(brand_id, alias),
  FOREIGN KEY (brand_id) REFERENCES brands(id)
);
CREATE TABLE IF NOT EXISTS collections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL, -- 'brand' | 'category' | 'promo'
  name TEXT NOT NULL,
  slug TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  title TEXT,
  brand_id INTEGER,
  sku TEXT,
  gtin TEXT,
  description_html TEXT,
  currency TEXT,
  price REAL,
  stock_status TEXT,
  category_path TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_id) REFERENCES brands(id)
);
CREATE TABLE IF NOT EXISTS media (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  position INTEGER DEFAULT 0,
  FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS collection_items (
  collection_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  PRIMARY KEY (collection_id, product_id),
  FOREIGN KEY (collection_id) REFERENCES collections(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn

def seed_brands(conn: sqlite3.Connection, brands: List[Dict[str, Any]]):
    for b in brands:
        conn.execute(
            "INSERT OR IGNORE INTO brands(name, slug, status) VALUES(?,?,?)",
            (b["name"], b.get("slug"), b.get("status","active"))
        )
    conn.commit()

def upsert_brand_aliases(conn: sqlite3.Connection, aliases: List[Dict[str, Any]]):
    for a in aliases:
        cur = conn.execute("SELECT id FROM brands WHERE name = ?", (a["brand"],))
        row = cur.fetchone()
        if not row:
            conn.execute("INSERT INTO brands(name, status) VALUES(?,?)", (a["brand"], "draft"))
            brand_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            brand_id = row[0]
        conn.execute(
            "INSERT OR IGNORE INTO brand_aliases(brand_id, alias, priority) VALUES(?,?,?)",
            (brand_id, a["alias"], a.get("priority",1))
        )
    conn.commit()

def get_or_create_brand_collection(conn: sqlite3.Connection, brand_name: str) -> int:
    row = conn.execute("SELECT id FROM brands WHERE name = ?", (brand_name,)).fetchone()
    if not row:
        conn.execute("INSERT INTO brands(name, status) VALUES(?,?)", (brand_name, "draft"))
    slug = brand_name.lower().replace(' ', '-')
    conn.execute("INSERT OR IGNORE INTO collections(type, name, slug) VALUES(?,?,?)",
                 ("brand", brand_name, slug))
    cid = conn.execute("SELECT id FROM collections WHERE slug=?", (slug,)).fetchone()[0]
    conn.commit()
    return cid

def upsert_product(conn: sqlite3.Connection, product: Dict[str, Any]) -> int:
    existing = conn.execute("SELECT id FROM products WHERE url = ?", (product["url"],)).fetchone()
    if existing:
        pid = existing[0]
        conn.execute("""UPDATE products
            SET title=?, brand_id=?, sku=?, gtin=?, description_html=?, currency=?, price=?, stock_status=?, category_path=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (
            product.get("title"),
            product.get("brand_id"),
            product.get("sku"),
            product.get("gtin"),
            product.get("description_html"),
            product.get("currency"),
            product.get("price"),
            product.get("stock_status"),
            product.get("category_path"),
            pid
        ))
    else:
        cur = conn.execute("""INSERT INTO products
            (source, url, title, brand_id, sku, gtin, description_html, currency, price, stock_status, category_path)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            product["source"],
            product["url"],
            product.get("title"),
            product.get("brand_id"),
            product.get("sku"),
            product.get("gtin"),
            product.get("description_html"),
            product.get("currency"),
            product.get("price"),
            product.get("stock_status"),
            product.get("category_path"),
        ))
        pid = cur.lastrowid
    conn.commit()
    return pid

def replace_media(conn: sqlite3.Connection, product_id: int, image_urls: List[str]):
    conn.execute("DELETE FROM media WHERE product_id = ?", (product_id,))
    for i, url in enumerate(image_urls or []):
        conn.execute("INSERT INTO media(product_id, url, position) VALUES(?,?,?)", (product_id, url, i))
    conn.commit()

def attach_to_collection(conn: sqlite3.Connection, collection_id: int, product_id: int):
    conn.execute("INSERT OR IGNORE INTO collection_items(collection_id, product_id) VALUES(?,?)", (collection_id, product_id))
    conn.commit()

def export_products_json(conn: sqlite3.Connection, out_path: str):
    rows = conn.execute("""
    SELECT p.id, p.title, p.url, p.currency, p.price, p.stock_status, p.category_path,
           b.name as brand, GROUP_CONCAT(m.url, '|') as images
    FROM products p
    LEFT JOIN brands b ON p.brand_id = b.id
    LEFT JOIN media m ON m.product_id = p.id
    GROUP BY p.id
    ORDER BY p.id DESC
    """).fetchall()
    cols = ["id","title","url","currency","price","stock_status","category_path","brand","images"]
    data = [dict(zip(cols, r)) for r in rows]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
