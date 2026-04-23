from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.fpt_database # Thay bằng db tương ứng của An
collection = db.iphone_full_data
def fix_database_duplicates():
    cursor = collection.find({})
    for product in cursor:
        history = product.get('price_history', [])
        if not history: continue

        # Lọc trùng bằng dict
        unique_history = {item['date']: item for item in history}
        new_history = list(unique_history.values())

        # Cập nhật lại vào MongoDB
        collection.update_one(
            {"_id": product["_id"]},
            {"$set": {"price_history": new_history}}
        )
    print("✅ Đã dọn dẹp sạch các bản ghi trùng ngày trong Database!")

fix_database_duplicates()