
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any, List, Optional
from .normalize import normalize_text, parse_price

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; UM-Importer/0.1; +https://ukrainemart.example)"
}

def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text

def crawl_listing(start_url: str, product_link_sel: str, pagination_next_sel: Optional[str]) -> List[str]:
    urls, to_visit = [], [start_url]
    seen = set()
    while to_visit:
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)
        html = fetch_html(url)
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
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    def get_text(sel: Optional[str]):
        el = soup.select_one(sel) if sel else None
        return normalize_text(el.get_text(strip=True)) if el else None
    def get_html(sel: Optional[str]):
        el = soup.select_one(sel) if sel else None
        return str(el) if el else None

    title = get_text(conf.get("title_selector"))
    brand_raw = get_text(conf.get("brand_selector"))
    description_html = get_html(conf.get("description_selector"))
    price_raw = get_text(conf.get("price_selector"))
    price = parse_price(price_raw)
    sku = get_text(conf.get("sku_selector"))
    gtin = get_text(conf.get("gtin_selector"))
    currency = conf.get("currency") or "UAH"
    stock = get_text(conf.get("stock_selector"))
    images = []
    img_sel = conf.get("image_selector")
    if img_sel:
        for img in soup.select(img_sel):
            src = img.get("src") or img.get("data-src")
            if src:
                images.append(urljoin(url, src))
    cat = None
    bc_sel = conf.get("category_breadcrumb_selector")
    if bc_sel:
        cats = [el.get_text(strip=True) for el in soup.select(bc_sel)]
        if cats:
            cat = " > ".join(cats)
    return {
        "url": url,
        "title": title,
        "brand_raw": brand_raw,
        "description_html": description_html,
        "currency": currency,
        "price": price,
        "price_raw": price_raw,
        "sku": sku,
        "gtin": gtin,
        "images": images,
        "stock_status": stock,
        "category_path": cat
    }
