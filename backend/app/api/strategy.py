"""策略相关接口"""
from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import select, desc, func, delete

from app.core.database import async_session
from app.models.stock import StrategyResult, StrategyTemplate, DailyKline, Stock
from app.schemas.stock import (
    StrategyRunRequest, StrategyResultOut, StrategyResultResponse, StrategyRunResponse,
)
from app.services.strategy import run_strategy_with_steps, parse_strategy_text
from app.services.eastmoney_client import eastmoney_client

router = APIRouter(prefix="/strategy", tags=["策略"])


@router.post("/run", summary="执行自定义策略", response_model=StrategyRunResponse)
async def api_run_strategy(req: StrategyRunRequest):
    result = await run_strategy_with_steps(
        trade_date=req.trade_date,
        strategy_text=req.strategy_text,
        strategy_name=req.strategy_name,
    )
    return result


@router.post("/parse", summary="解析策略文本(仅解析不执行)")
async def api_parse_strategy(strategy_text: str):
    conditions = parse_strategy_text(strategy_text)
    return {"conditions": conditions}


@router.get("/results", summary="查询策略筛选结果", response_model=StrategyResultResponse)
async def api_get_results(
    trade_date: date = Query(..., description="交易日期"),
    strategy_name: str = Query(default="竞价低吸", description="策略名称"),
):
    async with async_session() as db:
        query = (
            select(StrategyResult)
            .where(
                StrategyResult.trade_date == trade_date,
                StrategyResult.strategy_name == strategy_name,
            )
            .order_by(desc(StrategyResult.auction_amount))
        )
        result = await db.execute(query)
        items = result.scalars().all()
    return StrategyResultResponse(
        trade_date=trade_date,
        strategy_name=strategy_name,
        count=len(items),
        results=[StrategyResultOut.model_validate(i) for i in items],
    )


@router.get("/history", summary="查询历史筛选记录")
async def api_get_history(
    strategy_name: str = Query(default="竞价低吸"),
    limit: int = Query(default=30, le=100),
):
    async with async_session() as db:
        query = (
            select(StrategyResult.trade_date, func.count(StrategyResult.id).label("count"))
            .where(StrategyResult.strategy_name == strategy_name)
            .group_by(StrategyResult.trade_date)
            .order_by(desc(StrategyResult.trade_date))
            .limit(limit)
        )
        result = await db.execute(query)
        rows = result.all()
    return [{"trade_date": r.trade_date, "count": r.count} for r in rows]


@router.post("/run-batch", summary="批量执行策略(多天)")
async def api_run_batch(req: StrategyRunRequest, days: int = Query(default=7, le=30)):
    from datetime import timedelta
    results = []
    base_date = req.trade_date

    for i in range(days):
        trade_date = base_date - timedelta(days=i)
        try:
            result = await run_strategy_with_steps(
                trade_date=trade_date,
                strategy_text=req.strategy_text,
                strategy_name=req.strategy_name,
            )
            results.append({"date": trade_date, "count": result["count"], "success": True})
        except Exception as e:
            results.append({"date": trade_date, "error": str(e), "success": False})

    return {"results": results}


@router.get("/templates", summary="获取策略模板列表")
async def api_get_templates():
    async with async_session() as db:
        result = await db.execute(select(StrategyTemplate).order_by(desc(StrategyTemplate.created_at)))
        templates = result.scalars().all()
    return [{"id": t.id, "name": t.name, "content": t.content} for t in templates]


@router.post("/templates", summary="保存策略模板")
async def api_save_template(name: str, content: str):
    async with async_session() as db:
        await db.execute(delete(StrategyTemplate).where(StrategyTemplate.name == name))
        template = StrategyTemplate(name=name, content=content)
        db.add(template)
        await db.commit()
    return {"success": True}


@router.delete("/templates/{template_id}", summary="删除策略模板")
async def api_delete_template(template_id: int):
    async with async_session() as db:
        await db.execute(delete(StrategyTemplate).where(StrategyTemplate.id == template_id))
        await db.commit()
    return {"success": True}


def _board_label_from_code(code: str) -> str:
    if code.startswith("688"):
        return "科创板"
    if code.startswith("3"):
        return "创业板"
    if code.startswith(("4", "8")):
        return "北交所"
    return "主板"


@router.get("/limitup", summary="获取当天涨停池数据(本地数据库)")
async def api_get_limitup(_trade_date: date | None = Query(default=None, alias="trade_date")):
    requested_date = _trade_date or date.today()

    # 当天涨停池：优先东方财富（更实时）；失败再降级查本地库
    if requested_date == date.today():
        try:
            items = await eastmoney_client.get_limit_up_pool(requested_date)
            data = [
                {
                    "code": item.get("c", ""),
                    "name": item.get("n", ""),
                    "board": _board_label_from_code(item.get("c", "") or ""),
                    "close": round(float(item.get("p", 0) or 0) / 1000, 3),
                    "change_pct": float(item.get("zdp", 0) or 0),
                    "limit_up_time": item.get("fbt"),
                    "last_limit_up_time": item.get("lbt"),
                    "open_count": int(item.get("zbc", 0) or 0),
                    "limit_up_count": int(item.get("lbc", 0) or 0),
                    "amount": float(item.get("amount", 0) or 0),
                    "sealed_fund": float(item.get("fund", 0) or 0),
                    "raw": item,
                }
                for item in items
                if isinstance(item, dict)
            ]
            return {"date": requested_date, "count": len(data), "source": "eastmoney", "data": data}
        except Exception as e:
            # 不中断，走本地库兜底
            pass

    async with async_session() as db:
        result = await db.execute(
            select(
                DailyKline.code,
                Stock.name,
                DailyKline.close,
                DailyKline.amount,
                DailyKline.change_pct,
            )
            .join(Stock, Stock.code == DailyKline.code)
            .where(DailyKline.trade_date == requested_date, DailyKline.is_limit_up.is_(True))
            .order_by(desc(DailyKline.amount))
        )
        rows = result.all()

    data = [
        {
            "code": code,
            "name": name,
            "board": _board_label_from_code(code),
            "close": float(close) if close is not None else None,
            "amount": float(amount) if amount is not None else None,
            "change_pct": float(change_pct) if change_pct is not None else None,
        }
        for code, name, close, amount, change_pct in rows
    ]
    return {"date": requested_date, "count": len(data), "source": "db", "data": data}

