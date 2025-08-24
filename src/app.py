from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
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
    c = conn.cursor()
    c.execute(
        "SELECT p.id, p.title, p.price, p.currency, "
        "(SELECT url FROM media WHERE product_id=p.id LIMIT 1) as photo, "
        "b.name as brand "
        "FROM products p LEFT JOIN brands b ON p.brand_id=b.id "
        "ORDER BY p.id DESC"
    )
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return rows_to_dicts(rows, cols)


@app.get("/product/{product_id}")
@app.get("/product")
def product_detail(request: Request, product_id: int = Query(None)):
    """Підтримка і /product/11 і /product?id=11"""
    if product_id is None:
        product_id = request.query_params.get("id")
    if not product_id:
        return HTMLResponse("<h3>Не знайдено</h3>", status_code=404)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, title, description_html, price, currency "
        "FROM products WHERE id=?",
        (product_id,),
    )
    row = c.fetchone()

    # фото
    c.execute("SELECT url FROM media WHERE product_id=?", (product_id,))
    photos = [r[0] for r in c.fetchall()]

    # розміри
    c.execute("SELECT value FROM options WHERE product_id=?", (product_id,))
    options = [r[0] for r in c.fetchall()]
    conn.close()

    if not row:
        return HTMLResponse("<h3>Не знайдено</h3>", status_code=404)

    product = {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "price": row[3],
        "currency": row[4],
        "photos": photos,
        "options": options,
    }
    return JSONResponse(product)


@app.get("/")
def index():
    with open("web/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

