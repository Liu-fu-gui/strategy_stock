import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from app.core.database import async_session
from app.models.stock import StrategyResult

async def check_history():
    async with async_session() as db:
        # 查询最近7天的记录
        seven_days_ago = datetime.now().date() - timedelta(days=7)

        query = (
            select(
                StrategyResult.trade_date,
                StrategyResult.strategy_name,
                func.count(StrategyResult.id).label("count")
            )
            .where(StrategyResult.trade_date >= seven_days_ago)
            .group_by(StrategyResult.trade_date, StrategyResult.strategy_name)
            .order_by(desc(StrategyResult.trade_date))
        )

        result = await db.execute(query)
        rows = result.all()

        print(f"\n最近7天的选股记录 (从 {seven_days_ago} 开始):")
        print("-" * 60)
        for row in rows:
            print(f"日期: {row.trade_date}, 策略: {row.strategy_name}, 数量: {row.count}")

        if not rows:
            print("没有找到记录")

if __name__ == "__main__":
    asyncio.run(check_history())
