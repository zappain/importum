from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")

DB_PATH = "um.db"

def rows_to_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in cursor.fetchall()]

@app.get("/")
def home():
    index_file = Path("web/static/index.html")
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>Index not found</h2>", status_code=404)

@app.get("/products")
def products():
    if not Path(DB_PATH).exists():
        return JSONResponse([])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.title, p.price, p.currency,
               (SELECT url FROM media WHERE product_id=p.id LIMIT 1) as thumbnail
        FROM products p
        ORDER BY p.id DESC
        LIMIT 100;
    """)
    rows = rows_to_dicts(c)
    conn.close()
    return JSONResponse(rows)

@app.get("/product/{product_id}")
def product_detail(product_id: int):
    if not Path(DB_PATH).exists():
        return JSONResponse({"error": "DB not found"}, status_code=500)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # основні поля
    c.execute("""
        SELECT id, title, description_html, price, currency
        FROM products
        WHERE id=?;
    """, (product_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return JSONResponse({"error": "Not found"}, status_code=404)

    product = {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "price": row[3],
        "currency": row[4],
        "photos": [],
        "sizes": []
    }

    # фото
    try:
        c.execute("SELECT url FROM media WHERE product_id=? ORDER BY position ASC;", (product_id,))
        product["photos"] = [r[0] for r in c.fetchall()]
    except sqlite3.OperationalError:
        product["photos"] = []

    # розміри (опції)
    try:
        c.execute("SELECT value FROM options WHERE product_id=?;", (product_id,))
        product["sizes"] = [r[0] for r in c.fetchall()]
    except sqlite3.OperationalError:
        product["sizes"] = []

    conn.close()
    return JSONResponse(product)
