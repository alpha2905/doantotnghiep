from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"

async def test():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    # Check iphone
    print("--- iPhone names ---")
    cursor = db.iphone_master_data.find().limit(10)
    async for doc in cursor:
        print(doc.get('name'))
    
    # Check samsung
    print("\n--- Samsung names ---")
    cursor = db.samsung_master_data.find().limit(10)
    async for doc in cursor:
        print(doc.get('name'))
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(test())
