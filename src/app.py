from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
from pathlib import Path

app = FastAPI()

# підключаємо папку зі статикою
app.mount("/static", StaticFiles(directory="web/static"), name="static")

DB_PATH = "um.db"

def row_to_dict(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@app.get("/", response_class=HTMLResponse)
def home():
    index_file = Path("web/static/index.html")
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return HTMLResponse("<h2>Index not found</h2>", status_code=404)

@app.get("/products")
def products():
    if not Path(DB_PATH).exists():
        return JSONResponse([])
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = row_to_dict
    c = conn.cursor()
    c.execute("SELECT id, title, price, currency FROM products LIMIT 50;")
    rows = c.fetchall()
    conn.close()
    return rows

@app.get("/product/{product_id}")
@app.get("/product")
def product_detail(product_id: int = Query(None)):
    # якщо product_id немає - пробуємо взяти з query (?id=..)
    if not product_id:
        return HTMLResponse("<h3>Не знайдено</h3>", status_code=404)

    if not Path(DB_PATH).exists():
        return HTMLResponse("<h3>DB not found</h3>", status_code=500)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, description_html FROM products WHERE id=?;", (product_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return HTMLResponse("<h3>Не знайдено</h3>", status_code=404)

    # простий HTML для карточки товару
    return HTMLResponse(f"""
        <a href="/">← Назад до каталогу</a>
        <h1>{row[1]}</h1>
        <div>{row[2] or "Опису нема"}</div>
    """)

