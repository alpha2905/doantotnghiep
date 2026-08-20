import asyncio
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"

STORE_COLLECTIONS = {
    "FPT Shop": "fpt",
    "Thế Giới Di Động": "tgdd",
    "CellphoneS": "cellphones",
    "Hoàng Hà Mobile": "hoangha",
    "Di Động Việt": "didongviet",
    "Viettel Store": "viettelstore",
    "Clickbuy": "clickbuy",
    "MobileCity": "mobilecity",
}

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    print(f"=== KIỂM TRA COMMENT THEO TỪNG SÀN (DB: {MONGO_DB}) ===\n")
    print(f"{'Sàn':<25} {'Tổng SP':<10} {'SP có cmt':<12} {'SP không cmt':<15} {'Tổng cmt':<12}")
    print("-" * 80)

    total_products = 0
    total_with_comments = 0
    total_comments = 0

    for store_name, col_name in STORE_COLLECTIONS.items():
        col = db[col_name]
        total = await col.count_documents({})
        # Đếm sản phẩm có comments (list không rỗng)
        with_comments = await col.count_documents({
            "comments": {"$exists": True, "$ne": [], "$type": "array"}
        })
        # Đếm sản phẩm có comments là string không rỗng
        with_comments_str = await col.count_documents({
            "comments": {"$exists": True, "$type": "string", "$ne": ""}
        })
        with_comments_total = with_comments + with_comments_str
        without_comments = total - with_comments_total

        # Tổng số comment (chỉ tính array)
        total_cmt = 0
        cursor = col.find({"comments": {"$exists": True, "$type": "array"}}, {"comments": 1})
        async for doc in cursor:
            total_cmt += len(doc.get("comments", []) or [])

        total_products += total
        total_with_comments += with_comments_total
        total_comments += total_cmt

        status = "✅" if with_comments_total > 0 else "❌"
        print(f"{store_name:<25} {total:<10} {with_comments_total:<12} {without_comments:<15} {total_cmt:<12} {status}")

    print("-" * 80)
    print(f"{'TỔNG':<25} {total_products:<10} {total_with_comments:<12} {'':<15} {total_comments:<12}")
    print()
    print("KẾT LUẬN:")
    missing_stores = []
    store_names = list(STORE_COLLECTIONS.keys())
    for idx, col_name in enumerate(STORE_COLLECTIONS.values()):
        arr_count = await db[col_name].count_documents({"comments": {"$exists": True, "$ne": [], "$type": "array"}})
        str_count = await db[col_name].count_documents({"comments": {"$exists": True, "$type": "string", "$ne": ""}})
        if arr_count + str_count == 0:
            missing_stores.append(store_names[idx])
    if not missing_stores:
        print("✅ Tất cả 8 sàn đều có comment!")
    else:
        print(f"❌ Các sàn CHƯA có comment: {', '.join(missing_stores)}")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())