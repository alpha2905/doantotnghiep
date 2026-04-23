from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.tgdd_database
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
