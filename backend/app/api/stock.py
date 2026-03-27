"""股票查询接口"""
from fastapi import APIRouter, Query
from sqlalchemy import select, or_

from app.core.database import async_session
from app.models.stock import DailyKline, Stock
from app.schemas.stock import DailyKlineOut, StockOut

router = APIRouter(prefix="/stocks", tags=["股票"])


@router.get("", summary="查询股票列表", response_model=list[StockOut])
async def api_stock_list(
    keyword: str = Query(default="", description="代码或名称关键词"),
    board: str = Query(default="", description="板块筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    query = select(Stock).where(Stock.is_active == 1)

    kw = keyword.strip()
    if kw:
        like_kw = f"%{kw}%"
        query = query.where(or_(Stock.code.ilike(like_kw), Stock.name.ilike(like_kw)))

    async with async_session() as db:
        result = await db.execute(query.order_by(Stock.code.asc()))
        items = result.scalars().all()

    if board:
        items = [item for item in items if item.board == board]

    start = (page - 1) * page_size
    end = start + page_size
    return [StockOut.model_validate(item) for item in items[start:end]]


@router.get("/{code}/kline", summary="查询股票K线", response_model=list[DailyKlineOut])
async def api_stock_kline(code: str, limit: int = Query(default=60, ge=1, le=240)):
    async with async_session() as db:
        result = await db.execute(
            select(DailyKline)
            .where(DailyKline.code == code)
            .order_by(DailyKline.trade_date.desc())
            .limit(limit)
        )
        items = result.scalars().all()
    return [DailyKlineOut.model_validate(item) for item in items]
