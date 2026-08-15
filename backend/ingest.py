import argparse
import asyncio
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient
from backend import schema


async def ingest_records(mongo_uri: str, platform: str, brand: str, file_path: str, collection_override: str = None):
    client = AsyncIOMotorClient(mongo_uri)
    db = client["price_tracker"]
    db_map = {
        "fpt": db,
        "tgdd": db,
        "dmx": db,
    }
    if platform not in db_map:
        raise ValueError(f"Unknown platform: {platform}")

    is_jsonl = file_path.lower().endswith(".jsonl") or file_path.lower().endswith(".ndjson")
    count = 0
    async def process_item(item):
        nonlocal count
        # allow record to specify its own platform/brand
        rec_platform = item.get("platform") or platform
        rec_brand = item.get("brand") or brand
        normalized = schema.normalize_product(item, brand=rec_brand, platform=rec_platform)
        col_name = collection_override or (f"{rec_brand}_full_data" if rec_platform == "fpt" else (f"{rec_brand}_master_data" if rec_platform == "tgdd" else f"{rec_brand}_products"))
        await schema.upsert_product(db, col_name, normalized)
        count += 1

    if is_jsonl:
        with open(file_path, "r", encoding="utf-8") as fh:
            tasks = []
            for line in fh:
                line = line.strip()
                if not line: continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                tasks.append(process_item(obj))
            if tasks:
                # run sequentially to avoid overloading DB
                for t in tasks:
                    await t
    else:
        with open(file_path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
            # Accept list or single object
            if isinstance(obj, list):
                for item in obj:
                    await process_item(item)
            elif isinstance(obj, dict):
                await process_item(obj)

    print(f"Ingest finished. Records processed: {count}")


def main():
    parser = argparse.ArgumentParser(description="Batch ingest product data into MongoDB using project schema normalization.")
    parser.add_argument("--file", "-f", required=True, help="Path to JSON or JSONL file to ingest")
    parser.add_argument("--platform", "-p", required=True, choices=["fpt", "tgdd", "dmx"], help="Platform key (fpt|tgdd|dmx)")
    parser.add_argument("--brand", "-b", required=True, help="Brand key (iphone|samsung|oppo|xiaomi, etc.)")
    parser.add_argument("--mongo", default="mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham", help="MongoDB URI")
    parser.add_argument("--collection", default=None, help="Optional collection name override")

    args = parser.parse_args()
    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        raise SystemExit(f"File not found: {file_path}")

    asyncio.run(ingest_records(args.mongo, args.platform, args.brand, file_path, args.collection))


if __name__ == "__main__":
    main()
