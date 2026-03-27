"""数据同步服务 - 从 xtick 拉取数据写入数据库"""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.redis import redis_client
from app.models.stock import Stock, DailyKline, AuctionData
from app.services.xtick_client import xtick_client, XtickApiError

logger = logging.getLogger(__name__)


def _classify_board(code: str, name: str) -> tuple[str, str, bool]:
    market = "sz" if code.startswith(("0", "3")) else "sh" if code.startswith(("6",)) else "bj"
    if code.startswith("688"):
        board = "kcb"
    elif code.startswith("3"):
        board = "cyb"
    elif code.startswith(("4", "8")):
        board = "bj"
    else:
        board = "main"
    is_st = "ST" in name.upper()
    return market, board, is_st


def _calc_change_pct(close: float, pre_close: float) -> float:
    if pre_close == 0:
        return 0
    return round((close - pre_close) / pre_close * 100, 4)


def _is_limit_up(close: float, pre_close: float, code: str) -> bool:
    if pre_close == 0:
        return False
    pct = (close - pre_close) / pre_close * 100
    if code.startswith(("688", "3")):
        return pct >= 19.5
    return pct >= 9.5


async def sync_stock_list():
    """同步股票列表"""
    try:
        data = await xtick_client.get_stock_list("all")
    except (XtickApiError, Exception) as e:
        logger.error(f"同步股票列表失败: {e}")
        return 0

    if not data:
        return 0

    rows = []
    now = datetime.now()
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("type") != 1:
            continue
        code = item.get("code", "")
        name = item.get("name", "")
        if not code:
            continue
        market, _, _ = _classify_board(code, name)
        rows.append({"code": code, "name": name, "market": market, "is_active": 1, "updated_at": now})

    if not rows:
        return 0

    async with async_session() as db:
        for i in range(0, len(rows), 500):
            batch = rows[i:i+500]
            stmt = pg_insert(Stock).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code"],
                set_={"name": stmt.excluded.name, "market": stmt.excluded.market,
                       "is_active": 1, "updated_at": now},
            )
            await db.execute(stmt)
        await db.commit()
    logger.info(f"同步股票列表完成, 共 {len(rows)} 只")
    return len(rows)


async def sync_daily_kline(trade_date: date):
    """同步全市场某日日K数据"""
    try:
        data = await xtick_client.get_all_daily_kline(trade_date)
    except (XtickApiError, Exception) as e:
        logger.error(f"同步 {trade_date} 日K失败: {e}")
        return 0

    if not data:
        return 0

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = item.get("code", "")
        if not code:
            continue
        close_price = float(item.get("close", 0))
        pre_close = float(item.get("preClose", 0))
        rows.append({
            "code": code,
            "trade_date": trade_date,
            "open": item.get("open", 0),
            "high": item.get("high", 0),
            "low": item.get("low", 0),
            "close": close_price,
            "pre_close": pre_close,
            "volume": item.get("volume", 0),
            "amount": item.get("amount", 0),
            "change_pct": _calc_change_pct(close_price, pre_close),
            "is_limit_up": _is_limit_up(close_price, pre_close, code),
        })

    if not rows:
        return 0

    async with async_session() as db:
        for i in range(0, len(rows), 100):
            batch = rows[i:i+100]
            stmt = pg_insert(DailyKline).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code", "trade_date"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "pre_close": stmt.excluded.pre_close,
                    "volume": stmt.excluded.volume,
                    "amount": stmt.excluded.amount,
                    "change_pct": stmt.excluded.change_pct,
                    "is_limit_up": stmt.excluded.is_limit_up,
                },
            )
            await db.execute(stmt)
        await db.commit()
    logger.info(f"同步 {trade_date} 日K完成, {len(rows)} 条")
    return len(rows)


async def sync_auction_data(trade_date: date):
    """同步全市场某日竞价数据(REST API)"""
    try:
        data = await xtick_client.get_all_history_auction(trade_date)
    except (XtickApiError, Exception) as e:
        logger.error(f"同步 {trade_date} 竞价失败: {e}")
        return 0

    if not data:
        return 0

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = item.get("code", "")
        if not code:
            continue
        rows.append({
            "code": code,
            "trade_date": trade_date,
            "price": item.get("price", 0),
            "pre_close": item.get("close", 0),
            "auction_change_pct": item.get("jjzf", 0),
            "auction_volume": item.get("jjl", 0),
            "auction_amount": item.get("jje", 0),
            "unmatched_volume": item.get("nol"),
            "unmatched_amount": item.get("noe"),
            "trend": item.get("trend"),
        })

    if not rows:
        return 0

    async with async_session() as db:
        for i in range(0, len(rows), 100):
            batch = rows[i:i+100]
            stmt = pg_insert(AuctionData).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code", "trade_date"],
                set_={
                    "price": stmt.excluded.price,
                    "pre_close": stmt.excluded.pre_close,
                    "auction_change_pct": stmt.excluded.auction_change_pct,
                    "auction_volume": stmt.excluded.auction_volume,
                    "auction_amount": stmt.excluded.auction_amount,
                    "unmatched_volume": stmt.excluded.unmatched_volume,
                    "unmatched_amount": stmt.excluded.unmatched_amount,
                    "trend": stmt.excluded.trend,
                },
            )
            await db.execute(stmt)
        await db.commit()
    logger.info(f"同步 {trade_date} 竞价完成, {len(rows)} 条")
    return len(rows)


async def sync_recent_klines(trade_date: date, days: int = 10):
    """补齐历史日K, 跳过已有数据"""
    async with async_session() as db:
        result = await db.execute(
            select(DailyKline.trade_date).distinct()
            .where(DailyKline.trade_date >= trade_date - timedelta(days=days + 5))
        )
        existing_dates = {r[0] for r in result.all()}

    total = 0
    for i in range(1, days + 1):
        d = trade_date - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        if d in existing_dates:
            continue
        try:
            count = await sync_daily_kline(d)
            total += count
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"同步 {d} 日K失败: {e}")
    return total


async def cache_quant_data() -> int:
    """同步流通市值到数据库, 每天调一次即可"""
    try:
        quant_data = await xtick_client.get_quant_data("x025")
        cap_map = {}
        if isinstance(quant_data, dict) and "data" in quant_data:
            qdata = quant_data["data"]
            codes = qdata.get("code", [])
            caps = qdata.get("x025", [])
            for i, code in enumerate(codes):
                if i < len(caps) and caps[i]:
                    cap_map[code] = float(caps[i]) / 1e8
        if not cap_map:
            logger.warning("流通市值接口返回为空, 未写入数据库")
            return 0

        async with async_session() as db:
            from sqlalchemy import update
            for code, cap in cap_map.items():
                await db.execute(
                    update(Stock)
                    .where(Stock.code == code)
                    .values(circulating_market_cap=cap)
                )
            await db.commit()
        logger.info(f"流通市值已同步到数据库: {len(cap_map)} 只")
        return len(cap_map)
    except Exception as e:
        logger.warning(f"同步流通市值失败: {e}")
        return 0


async def ensure_market_cap_cache() -> int:
    """确保数据库中已有流通市值缓存, 避免服务重启后当日策略无市值可用。"""
    async with async_session() as db:
        existing_count = (
            await db.execute(
                select(func.count()).select_from(Stock).where(Stock.circulating_market_cap.is_not(None))
            )
        ).scalar() or 0

    if existing_count:
        logger.info(f"流通市值缓存已存在: {existing_count} 只")
        return existing_count

    logger.info("数据库中暂无流通市值缓存, 启动即时同步")
    return await cache_quant_data()


async def sync_all(trade_date: date):
    """同步数据: 股票列表 + 历史日K(不含当日) + 当日竞价 + 缓存市值"""
    stock_count = await sync_stock_list()
    history_kline_count = await sync_recent_klines(trade_date, days=12)
    auction_count = await sync_auction_data(trade_date)
    await cache_quant_data()
    return {
        "stocks": stock_count,
        "klines": history_kline_count,
        "auctions": auction_count,
    }
