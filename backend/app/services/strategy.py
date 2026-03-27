"""策略引擎 - 支持自定义条件的分步筛选"""
import json
import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.redis import redis_client
from app.models.stock import Stock, DailyKline, AuctionData, StrategyResult
from app.services.data_syncer import ensure_market_cap_cache
from app.services.xtick_client import xtick_client

logger = logging.getLogger(__name__)


def _build_market_cap_map(all_stocks: dict[str, Stock]) -> dict[str, float]:
    cap_map: dict[str, float] = {}
    for code, stock in all_stocks.items():
        if stock.circulating_market_cap is not None:
            cap_map[code] = float(stock.circulating_market_cap)
    return cap_map


def parse_strategy_text(text: str) -> list[dict]:
    """
    解析策略文本为条件列表。
    支持的条件关键词:
    - 近N日有涨停 / 近N日涨停次数>=M
    - 近N日回调超过X%
    - 竞价抢筹 / 竞价异动类型
    - 竞价金额大于X万/X万元
    - 流通市值大于X亿小于Y亿 / 市值>X亿
    - 非科创 / 不包含科创 / 排除科创
    - 非创业 / 不包含创业板
    - 非北交所 / 不包含北交所
    - 非ST / 不包含ST
    """
    conditions = []
    # 按逗号、分号、句号分割
    parts = re.split(r'[，,；;。\n]+', text.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 近N日有涨停
        m = re.search(r'近(\d+)日.*涨停', part)
        if m:
            conditions.append({
                "type": "limit_up_in_days",
                "days": int(m.group(1)),
                "label": f"近{m.group(1)}日的涨停次数",
            })
            continue

        # 近N日回调超过X%
        m = re.search(r'近(\d+)日.*回调.*?(\d+\.?\d*)%', part)
        if m:
            conditions.append({
                "type": "pullback",
                "days": int(m.group(1)),
                "threshold": float(m.group(2)),
                "label": f"近{m.group(1)}日回调幅度>{m.group(2)}%",
            })
            continue

        # 竞价抢筹 / 竞价异动
        if re.search(r'竞价.*(抢筹|异动)', part):
            conditions.append({
                "type": "auction_trend",
                "label": "竞价异动类型(抢筹)",
            })
            continue

        # 竞价金额大于X
        m = re.search(r'竞价金额.*?[大>].*?(\d+\.?\d*)\s*(万|亿)?', part)
        if m:
            amount = float(m.group(1))
            unit = m.group(2) or '万'
            if unit == '亿':
                amount *= 10000
            conditions.append({
                "type": "auction_amount",
                "min_amount": amount,  # 万元
                "label": f"竞价金额>{amount:.0f}万",
            })
            continue

        # 流通市值
        m = re.search(r'(?:流通)?市值.*?[大>].*?(\d+\.?\d*)\s*亿', part)
        if m:
            min_cap = float(m.group(1))
            max_cap = 99999
            m2 = re.search(r'小于(\d+\.?\d*)\s*亿|[<].*?(\d+\.?\d*)\s*亿', part)
            if m2:
                max_cap = float(m2.group(1) or m2.group(2))
            conditions.append({
                "type": "market_cap",
                "min_cap": min_cap,
                "max_cap": max_cap,
                "label": f"流通市值>{min_cap:.0f}亿" + (f"且<{max_cap:.0f}亿" if max_cap < 99999 else ""),
            })
            continue

        # 排除科创
        if re.search(r'(非|不含|不包含|排除).*科创', part):
            conditions.append({"type": "exclude_kcb", "label": "上市板块不包含科创"})
            continue

        # 排除创业板
        if re.search(r'(非|不含|不包含|排除).*创业', part):
            conditions.append({"type": "exclude_cyb", "label": "上市板块不包含创业板"})
            continue

        # 排除北交所
        if re.search(r'(非|不含|不包含|排除).*北交', part):
            conditions.append({"type": "exclude_bj", "label": "股票市场类型不包含北交所"})
            continue

        # 排除ST
        if re.search(r'(非|不含|不包含|排除).*[Ss][Tt]', part, re.IGNORECASE):
            conditions.append({"type": "exclude_st", "label": "股票简称不包含st"})
            continue

        # 无法识别的条件, 原样保留
        conditions.append({"type": "unknown", "label": part, "raw": part})

    return conditions


async def run_strategy_with_steps(
    trade_date: date,
    strategy_text: str,
    strategy_name: str = "自定义策略",
) -> dict:
    """
    分步执行策略, 返回每步筛选数量和最终结果。
    返回格式:
    {
        "strategy_name": "...",
        "trade_date": "2026-03-27",
        "conditions": [{"label": "...", "count": N}, ...],
        "count": N,
        "results": [...]
    }
    """
    conditions = parse_strategy_text(strategy_text)
    if not conditions:
        return {"strategy_name": strategy_name, "trade_date": str(trade_date),
                "conditions": [], "count": 0, "results": []}

    step_results = []  # 每步的过滤结果记录

    async with async_session() as db:
        # ========== 加载全量基础数据 ==========
        # 1) 所有A股
        stock_result = await db.execute(select(Stock))
        all_stocks = {s.code: s for s in stock_result.scalars().all()}
        # 当前候选集 (code set)
        candidates = set(all_stocks.keys())

        # 2) 预加载竞价数据
        auction_result = await db.execute(
            select(AuctionData).where(AuctionData.trade_date == trade_date)
        )
        auction_map = {a.code: a for a in auction_result.scalars().all()}

        # 3) 预加载近期K线数据 (近10个自然日覆盖5个交易日)
        kline_start = trade_date - timedelta(days=15)
        kline_result = await db.execute(
            select(DailyKline).where(
                DailyKline.trade_date >= kline_start,
                DailyKline.trade_date < trade_date,
            ).order_by(DailyKline.code, desc(DailyKline.trade_date))
        )
        kline_all = kline_result.scalars().all()
        # 按code分组
        kline_map: dict[str, list] = {}
        for k in kline_all:
            kline_map.setdefault(k.code, []).append(k)

        # 4) 从数据库加载流通市值
        cap_map = _build_market_cap_map(all_stocks)
        logger.info(f"流通市值数据(数据库): {len(cap_map)} 只")

        if any(cond["type"] == "market_cap" for cond in conditions) and not cap_map:
            logger.info("检测到市值条件且数据库无市值缓存, 开始即时同步流通市值")
            synced_count = await ensure_market_cap_cache()
            if synced_count:
                db.expire_all()
                stock_result = await db.execute(select(Stock))
                all_stocks = {s.code: s for s in stock_result.scalars().all()}
                cap_map = _build_market_cap_map(all_stocks)
            logger.info(f"流通市值数据(即时同步后): {len(cap_map)} 只")

        # 5) 行情数据直接使用已加载的竞价数据(不再调REST API)
        price_map: dict[str, dict] = {}
        for code, auction in auction_map.items():
            price_map[code] = {
                "price": float(auction.price) if auction.price else 0,
                "pre_close": float(auction.pre_close) if auction.pre_close else 0,
            }

        # ========== 逐条件筛选 ==========
        for cond in conditions:
            ctype = cond["type"]
            before_count = len(candidates)

            if ctype == "limit_up_in_days":
                days = cond["days"]
                passed = set()
                for code in candidates:
                    klines = kline_map.get(code, [])[:days]
                    if any(k.is_limit_up for k in klines):
                        passed.add(code)
                candidates = passed

            elif ctype == "pullback":
                days = cond["days"]
                threshold = cond["threshold"]
                passed = set()
                for code in candidates:
                    klines = kline_map.get(code, [])[:days]
                    if len(klines) < 2:
                        continue
                    # 从最早一根K线的前收盘到最新一根收盘
                    oldest_price = float(klines[-1].pre_close)
                    newest_price = float(klines[0].close)
                    if oldest_price == 0:
                        continue
                    pct = (newest_price - oldest_price) / oldest_price * 100
                    if pct < -threshold:
                        passed.add(code)
                candidates = passed

            elif ctype == "auction_trend":
                passed = set()
                for code in candidates:
                    auction = auction_map.get(code)
                    if auction and auction.trend == 1:
                        passed.add(code)
                candidates = passed

            elif ctype == "auction_amount":
                min_amount = cond["min_amount"] * 10000  # 万->元
                passed = set()
                for code in candidates:
                    auction = auction_map.get(code)
                    if auction and float(auction.auction_amount) >= min_amount:
                        passed.add(code)
                candidates = passed

            elif ctype == "market_cap":
                if not cap_map:
                    logger.warning("市值数据为空, 跳过市值筛选条件")
                else:
                    min_cap = cond["min_cap"]
                    max_cap = cond.get("max_cap", 99999)
                    passed = set()
                    for code in candidates:
                        cap = cap_map.get(code)
                        if cap is not None and min_cap <= cap <= max_cap:
                            passed.add(code)
                    candidates = passed

            elif ctype == "exclude_kcb":
                candidates = {c for c in candidates if all_stocks.get(c) and all_stocks[c].board != "kcb"}

            elif ctype == "exclude_cyb":
                candidates = {c for c in candidates if all_stocks.get(c) and all_stocks[c].board != "cyb"}

            elif ctype == "exclude_bj":
                candidates = {c for c in candidates if all_stocks.get(c) and all_stocks[c].board != "bj"}

            elif ctype == "exclude_st":
                candidates = {c for c in candidates if all_stocks.get(c) and not all_stocks[c].is_st}

            else:
                # 未知条件跳过
                pass

            step_results.append({
                "label": cond["label"],
                "count": len(candidates),
            })

        # ========== 构建最终结果 ==========
        results = []
        for code in candidates:
            stock = all_stocks.get(code)
            if not stock:
                continue
            auction = auction_map.get(code)
            klines = kline_map.get(code, [])

            # 现价和涨幅
            price_info = price_map.get(code, {})
            current_price = price_info.get("price", 0)
            pre_close = price_info.get("pre_close", 0)
            if current_price == 0 and auction:
                current_price = float(auction.price)
                pre_close = float(auction.pre_close)
            change_pct = 0.0
            if pre_close > 0:
                change_pct = round((current_price - pre_close) / pre_close * 100, 2)

            # 涨停满足条件日期
            limit_up_dates = []
            for k in klines[:5]:
                if k.is_limit_up:
                    limit_up_dates.append(str(k.trade_date))

            # 流通市值
            cap = cap_map.get(code)

            results.append({
                "code": code,
                "name": stock.name,
                "change_pct": change_pct,
                "current_price": current_price,
                "limit_up_dates": limit_up_dates,
                "auction_amount": float(auction.auction_amount) if auction else 0,
                "auction_change_pct": float(auction.auction_change_pct) if auction else 0,
                "trend": auction.trend if auction else 0,
                "circulating_market_cap": round(cap, 2) if cap else None,
            })

        # 按涨幅排序
        results.sort(key=lambda x: x["change_pct"], reverse=True)

        # ========== 保存到数据库(先清除同日旧结果) ==========
        await db.execute(
            delete(StrategyResult).where(
                StrategyResult.trade_date == trade_date,
                StrategyResult.strategy_name == strategy_name,
            )
        )
        for item in results:
            sr = StrategyResult(
                strategy_name=strategy_name,
                trade_date=trade_date,
                code=item["code"],
                name=item["name"],
                auction_amount=item["auction_amount"],
                auction_change_pct=item["auction_change_pct"],
                recent_limit_up_date=date.fromisoformat(item["limit_up_dates"][0]) if item["limit_up_dates"] else None,
                pullback_pct=None,
                circulating_market_cap=item.get("circulating_market_cap"),
                trend=item["trend"],
            )
            db.add(sr)
        await db.commit()

    return {
        "strategy_name": strategy_name,
        "trade_date": str(trade_date),
        "conditions": step_results,
        "count": len(results),
        "results": results,
    }
