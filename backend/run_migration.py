import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def run_migration():
    async with async_engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE stocks ADD COLUMN IF NOT EXISTS circulating_market_cap NUMERIC(20, 2)"
        ))
    print("Migration completed!")

if __name__ == "__main__":
    asyncio.run(run_migration())
