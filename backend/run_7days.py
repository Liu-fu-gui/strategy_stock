import asyncio
from datetime import datetime, timedelta
from app.services.strategy import run_strategy_with_steps

async def run_last_7_days():
    today = datetime.now().date()

    for i in range(7):
        trade_date = today - timedelta(days=i)
        print(f"\n{'='*60}")
        print(f"正在处理: {trade_date}")
        print(f"{'='*60}")

        try:
            result = await run_strategy_with_steps(
                trade_date=trade_date,
                strategy_text="竞价涨幅>3% AND 竞价涨幅<7% AND 竞价金额>5000万 AND 近期涨停后回调>5%",
                strategy_name="竞价低吸"
            )
            print(f"✓ {trade_date}: 筛选出 {result['count']} 只股票")
        except Exception as e:
            print(f"✗ {trade_date}: 失败 - {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_last_7_days())
