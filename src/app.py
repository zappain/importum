
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
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
    return JSONResponse(data)

@app.get("/")
def index():
    with open("web/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
