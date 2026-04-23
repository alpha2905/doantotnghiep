import re
from datetime import datetime
from typing import Any, Dict


def clean_product_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = name.replace("ip ", "iphone ")
    name = name.replace("ss ", "samsung ")
    name = name.replace("điện thoại", "").strip()
    return " ".join(name.split())


def extract_model_base(name: str) -> str:
    name = clean_product_name(name)
    name = re.sub(r'\d+\s*(gb|tb)', '', name)
    junk_words = ["chính hãng", "vn/a", "5g", "4g", "lte", "lắp sim", "hàng nhập khẩu"]
    for w in junk_words:
        name = name.replace(w, "")
    return " ".join(name.split())


def parse_price(price) -> int:
    try:
        p = str(price)
        p = re.sub(r'[^\d.]', '', p)
        if p == "":
            return 0
        return int(float(p))
    except:
        return 0


def normalize_product(raw: Dict[str, Any], brand: str, platform: str) -> Dict[str, Any]:
    name = raw.get("name") or raw.get("title") or raw.get("product_name") or ""
    image = raw.get("image") or raw.get("img") or ""
    url = raw.get("url") or raw.get("link") or raw.get("product_url") or ""
    price = raw.get("price") or raw.get("price_number") or raw.get("price_int") or 0
    price_number = parse_price(price)
    comments = raw.get("comments") or raw.get("reviews") or []
    if isinstance(comments, str):
        comments = [comments]
    now = datetime.utcnow().strftime("%Y-%m-%d")
    model_base = extract_model_base(name)
    normalized = {
        "platform": platform,
        "brand": brand,
        "name": name.strip(),
        "model_base": model_base,
        "price_number": int(price_number),
        "image": image,
        "url": url,
        "comments": comments,
        "price_history": raw.get("price_history", []) or [],
        "last_crawl": now,
    }
    # Ensure today's price in price_history if missing
    if price_number:
        ph = normalized["price_history"]
        if not ph or ph[-1].get("date") != now:
            ph.append({"date": now, "price": int(price_number)})
            normalized["price_history"] = ph
    return normalized


async def upsert_product(db, collection_name: str, product: Dict[str, Any]):
    """
    Upsert product into MongoDB collection.
    db: AsyncIOMotorDatabase
    """
    col = db[collection_name]
    if product.get("url"):
        filt = {"url": product["url"]}
    else:
        filt = {"name": product["name"], "brand": product["brand"]}

    existing = await col.find_one(filt)
    now = datetime.utcnow().strftime("%Y-%m-%d")
    if existing:
        last_price = existing.get("price_number", 0)
        cur_price = product.get("price_number", 0)
        updates = product.copy()
        updates["last_crawl"] = now
        if cur_price and cur_price != last_price:
            await col.update_one(filt, {"$set": updates, "$push": {"price_history": {"date": now, "price": cur_price}}})
        else:
            await col.update_one(filt, {"$set": updates})
    else:
        await col.insert_one(product)
