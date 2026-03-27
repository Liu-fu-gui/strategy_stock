"""定时任务调度"""
import logging
from datetime import date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.data_syncer import sync_stock_list, sync_daily_kline, sync_recent_klines, cache_quant_data
from app.services.strategy import run_strategy_with_steps
from app.services.ws_receiver import start_ws_receiver, save_final_auction

logger = logging.getLogger(__name__)
SH_TZ = ZoneInfo("Asia/Shanghai")

scheduler = AsyncIOScheduler(timezone=SH_TZ)

DEFAULT_STRATEGY = "近5日有涨停，近3日回调超过5%，竞价抢筹，竞价金额大于1000万，流通市值大于50亿小于300亿，非科创，非创业板，非北交所，非ST"


async def job_morning_prepare():
    """每天8:30 - 同步股票列表 + 补齐历史日K + 缓存流通市值"""
    today = date.today()
    logger.info(f"[8:30] 同步股票列表 + 补齐历史日K + 缓存流通市值")
    await sync_stock_list()
    await sync_recent_klines(today, days=12)
    await cache_quant_data()


async def job_start_ws():
    """每天9:14 - 启动 WebSocket 接收竞价数据"""
    logger.info("[9:14] 启动 WebSocket 接收竞价数据")
    await start_ws_receiver()


async def job_auction_strategy():
    """每天9:26 - 保存最终竞价数据 + 执行策略"""
    today = date.today()
    logger.info(f"[9:26] 保存竞价数据 + 执行策略 {today}")
    count = await save_final_auction()
    logger.info(f"[9:26] 竞价数据已保存: {count} 只")

    result = await run_strategy_with_steps(today, DEFAULT_STRATEGY, "竞价低吸")
    logger.info(f"[9:26] 策略结果: {result['count']} 只")
    for r in result.get("results", []):
        logger.info(f"  -> {r['code']} {r['name']} 竞价金额:{r['auction_amount']/10000:.0f}万")


async def job_after_close():
    """每天15:30 - 同步当日日K(为次日策略准备数据)"""
    today = date.today()
    logger.info(f"[15:30] 同步当日日K {today}")
    await sync_daily_kline(today)


def start_scheduler():
    # 8:30 同步股票列表+补齐历史K线
    scheduler.add_job(job_morning_prepare, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=30, timezone=SH_TZ
    ), id="morning_prepare")

    # 9:14 启动WebSocket接收竞价
    scheduler.add_job(job_start_ws, CronTrigger(
        day_of_week="mon-fri", hour=9, minute=14, timezone=SH_TZ
    ), id="start_ws")

    # 9:26 保存竞价+执行策略
    scheduler.add_job(job_auction_strategy, CronTrigger(
        day_of_week="mon-fri", hour=9, minute=26, timezone=SH_TZ
    ), id="auction_strategy")

    # 15:30 同步当日日K
    scheduler.add_job(job_after_close, CronTrigger(
        day_of_week="mon-fri", hour=15, minute=30, timezone=SH_TZ
    ), id="after_close")

    scheduler.start()
    logger.info("定时任务已启动(Asia/Shanghai): 8:30准备 -> 9:14 WS接收 -> 9:26选股 -> 15:30收盘")
    for job in scheduler.get_jobs():
        logger.info(f"任务 {job.id} 下次执行时间: {job.next_run_time}")


def stop_scheduler():
    scheduler.shutdown()
