import asyncio
import scrapers


async def update_prices_once():
    db = await scrapers.get_db()
    result = await scrapers.update_prices_real(db)
    return result.get("updated", 0)


async def price_updater_loop(interval_hours=3):
    while True:
        try:
            count = await update_prices_once()
            print(f"[PriceUpdater] Updated {count} products")
        except Exception as e:
            print(f"[PriceUpdater] Error: {e}")
        await asyncio.sleep(interval_hours * 3600)


if __name__ == "__main__":
    asyncio.run(update_prices_once())
