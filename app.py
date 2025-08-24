from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3, json
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")

DB_PATH = "um.db"

def rows_to_dicts(rows, cols):
    return [dict(zip(cols, r)) for r in rows]

@app.get("/products")
def products():
    if not Path(DB_PATH).exists():
        return JSONResponse([])
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        """
        SELECT p.id, p.title, p.url, p.currency, p.price, p.stock_status, p.category_path,
               IFNULL(b.name,'') as brand,
               IFNULL(GROUP_CONCAT(m.url, '|'),'') as images
        FROM products p
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN media m ON m.product_id = p.id
        GROUP BY p.id
        ORDER BY p.id DESC
        """
    )
    cols = ["id","title","url","currency","price","stock_status","category_path","brand","images"]
    data = rows_to_dicts(cur.fetchall(), cols)
    for d in data:
        imgs = (d.get("images") or "").split("|")
        d["thumbnail"] = imgs[0] if imgs and imgs[0] else ""
    return JSONResponse(data)

@app.get("/product/{pid}")
def product(pid: int):
    if not Path(DB_PATH).exists():
        return JSONResponse({}, status_code=404)
    conn = sqlite3.connect(DB_PATH)
    p = conn.execute("""
        SELECT p.id, p.title, p.url, p.currency, p.price, p.stock_status, p.category_path,
               IFNULL(b.name,'') as brand,
               IFNULL(p.description_html,'') as description_html,
               IFNULL(p.options_json,'') as options_json
        FROM products p
        LEFT JOIN brands b ON p.brand_id = b.id
        WHERE p.id = ?
    """, (pid,)).fetchone()
    if not p:
        return JSONResponse({}, status_code=404)
    cols = ["id","title","url","currency","price","stock_status","category_path","brand","description_html","options_json"]
    item = dict(zip(cols, p))
    rows = conn.execute("SELECT url FROM media WHERE product_id=? ORDER BY position ASC", (pid,)).fetchall()
    item["images"] = [r[0] for r in rows]
    try:
        item["options"] = json.loads(item.pop("options_json") or "{}")
    except Exception:
        item["options"] = {"sizes": []}
    return JSONResponse(item)

@app.get("/")
def index():
    with open("web/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
