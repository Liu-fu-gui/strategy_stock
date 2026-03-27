import asyncio
from sqlalchemy import select, func, distinct
from app.core.database import async_session
from app.models.stock import StrategyResult, AuctionData, DailyKline

async def check_data():
    async with async_session() as db:
        # 检查策略结果
        result = await db.execute(
            select(StrategyResult.trade_date, func.count(StrategyResult.id))
            .group_by(StrategyResult.trade_date)
            .order_by(StrategyResult.trade_date.desc())
        )
        print("策略结果:")
        for row in result.all():
            print(f"  {row[0]}: {row[1]} 只")

        # 检查竞价数据
        result = await db.execute(
            select(func.count(distinct(AuctionData.trade_date)))
        )
        print(f"\n竞价数据天数: {result.scalar()}")

        # 检查K线数据
        result = await db.execute(
            select(func.count(distinct(DailyKline.trade_date)))
        )
        print(f"K线数据天数: {result.scalar()}")

if __name__ == "__main__":
    asyncio.run(check_data())
