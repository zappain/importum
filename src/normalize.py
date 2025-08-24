
from typing import Dict, Any, Optional, Tuple, List
import re

def normalize_text(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip()

def parse_price(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    import re
    cleaned = re.sub(r"[^\d,\.\s]", "", s).strip()
    chunks = re.findall(r"[\d.,]+", cleaned)
    if not chunks:
        return None
    num = chunks[-1].replace(" ", "").replace(",", ".")
    try:
        return float(num)
    except:
        return None

def choose_brand(raw_brand: Optional[str], title: Optional[str], aliases: List[Dict[str, Any]], force_brand: Optional[str]=None) -> Tuple[Optional[str], float]:
    if force_brand:
        return force_brand, 1.0
    if raw_brand:
        rb_norm = raw_brand.strip().lower()
        for a in aliases:
            if a["alias"].lower() == rb_norm:
                return a["brand"], 0.95
    if title:
        t = title.lower()
        for a in aliases:
            if a["alias"].lower() in t:
                return a["brand"], 0.85
    return None, 0.0
