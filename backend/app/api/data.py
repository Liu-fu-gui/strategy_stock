"""数据同步相关接口"""
import asyncio
from datetime import date

from fastapi import APIRouter, BackgroundTasks

from app.schemas.stock import SyncRequest, SyncResponse
from app.services.data_syncer import sync_stock_list, sync_daily_kline, sync_auction_data, sync_all
from app.services.ws_receiver import start_ws_receiver, save_final_auction, get_ws_status

router = APIRouter(prefix="/data", tags=["数据同步"])


@router.post("/sync/stocks", summary="同步股票列表")
async def api_sync_stocks():
    count = await sync_stock_list()
    return {"count": count}


@router.post("/sync/kline", summary="同步日K线数据")
async def api_sync_kline(req: SyncRequest):
    count = await sync_daily_kline(req.trade_date)
    return {"trade_date": req.trade_date, "count": count}


@router.post("/sync/auction", summary="同步竞价数据(REST)")
async def api_sync_auction(req: SyncRequest):
    count = await sync_auction_data(req.trade_date)
    return {"trade_date": req.trade_date, "count": count}


@router.post("/sync/all", summary="同步全部数据", response_model=SyncResponse)
async def api_sync_all(req: SyncRequest):
    result = await sync_all(req.trade_date)
    return result


@router.post("/sync/batch", summary="批量同步多天数据")
async def api_sync_batch(req: SyncRequest, days: int = 7):
    from datetime import timedelta
    results = []
    for i in range(days):
        trade_date = req.trade_date - timedelta(days=i)
        try:
            result = await sync_all(trade_date)
            results.append({"date": trade_date, "success": True, **result})
        except Exception as e:
            results.append({"date": trade_date, "success": False, "error": str(e)})
    return {"results": results}


@router.post("/migrate/add-market-cap", summary="添加市值字段")
async def api_migrate_market_cap():
    from sqlalchemy import text
    from app.core.database import async_session
    try:
        async with async_session() as db:
            await db.execute(text(
                "ALTER TABLE stocks ADD COLUMN IF NOT EXISTS circulating_market_cap NUMERIC(20, 2)"
            ))
            await db.commit()
        return {"success": True, "message": "市值字段已添加"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/migrate/create-templates", summary="创建策略模板表")
async def api_migrate_templates():
    from sqlalchemy import text
    from app.core.database import async_session
    try:
        async with async_session() as db:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS strategy_templates (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    content VARCHAR(500) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await db.commit()
        return {"success": True, "message": "策略模板表已创建"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/ws/start", summary="手动启动WebSocket接收竞价")
async def api_ws_start(background_tasks: BackgroundTasks):
    background_tasks.add_task(start_ws_receiver)
    return {"message": "WebSocket 接收已启动(后台运行)"}


@router.post("/ws/save", summary="保存当前竞价缓存到数据库")
async def api_ws_save():
    count = await save_final_auction()
    return {"saved": count}


@router.get("/ws/status", summary="WebSocket接收状态")
async def api_ws_status():
    return get_ws_status()
