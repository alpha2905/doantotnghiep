import asyncio
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"

COLLECTIONS = ["fpt", "tgdd", "cellphones", "hoangha", "didongviet", "viettelstore", "clickbuy", "mobilecity"]

FIELDS_OF_INTEREST = [
    "rating", "sold", "shop_reputation", "positive_rate", "comments",
    "price_number", "price_history", "name", "url", "image"
]

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    print(f"=== Kiem tra field trong DB '{MONGO_DB}' ===\n")
    for col_name in COLLECTIONS:
        col = db[col_name]
        count = await col.count_documents({})
        print(f"--- Collection: {col_name} (so document: {count}) ---")
        if count == 0:
            print("  (rong)")
            continue
        sample = await col.find_one()
        if not sample:
            print("  (khong co du lieu)")
            continue
        for f in FIELDS_OF_INTEREST:
            val = sample.get(f)
            if val is not None:
                if isinstance(val, list):
                    shown = f"list[{len(val)}]"
                elif isinstance(val, dict):
                    shown = f"dict{list(val.keys())[:5]}"
                else:
                    shown = repr(val)[:60]
                print(f"  [OK] {f} = {shown}")
            else:
                print(f"  [MISSING] {f}")
        print()
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())