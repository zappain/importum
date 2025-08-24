import requests
from urllib.parse import urljoin
from typing import Dict, Any, List, Optional
from .normalize import normalize_text, parse_price

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UM-Importer/0.2; +https://ukrainemart.example)"}

def fetch_json(url: str) -> dict:
    api_url = url if url.endswith(".json") else url.rstrip("/") + ".json"
    resp = requests.get(api_url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.json()

def crawl_listing(start_url: str, product_link_sel: str, pagination_next_sel: Optional[str]) -> List[str]:
    # Тепер crawl_listing лишаємо як є, бо лістинг ми парсимо з HTML
    from bs4 import BeautifulSoup
    urls, to_visit = [], [start_url]
    seen = set()
    while to_visit:
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)
        html = requests.get(url, headers=HEADERS, timeout=25).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.select(product_link_sel):
            href = a.get("href")
            if href:
                urls.append(urljoin(url, href))
        if pagination_next_sel:
            nxt = soup.select_one(pagination_next_sel)
            if nxt and nxt.get("href"):
                to_visit.append(urljoin(url, nxt.get("href")))
    return list(dict.fromkeys(urls))

def parse_product(url: str, conf: Dict[str, Any]) -> Dict[str, Any]:
    data = fetch_json(url)
    product = data.get("product", {})

    title = normalize_text(product.get("title"))
    description_html = product.get("body_html")
    currency = conf.get("currency") or "UAH"

    # ---- ВАРІАНТИ (ціни, sku, розміри)
    variants = product.get("variants", [])
    price = None
    sku = None
    sizes = []
    if variants:
        price = parse_price(str(variants[0].get("price")))
        sku = variants[0].get("sku")
        for v in variants:
            opt = v.get("option1")
            if opt and opt.lower() not in ("default title",):
                sizes.append(opt)

    # ---- ФОТО
    images = [img.get("src") for img in product.get("images", []) if img.get("src")]

    return {
        "url": url,
        "title": title,
        "brand_raw": None,
        "description_html": description_html,
        "currency": currency,
        "price": price,
        "price_raw": str(price) if price else None,
        "sku": sku,
        "gtin": None,
        "images": images,
        "sizes": sizes,
        "stock_status": None,
        "category_path": None
    }
