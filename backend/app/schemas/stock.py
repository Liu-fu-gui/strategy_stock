from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StockOut(BaseModel):
    code: str
    name: str
    market: str
    board: str = ""
    is_st: bool = False

    class Config:
        from_attributes = True


class DailyKlineOut(BaseModel):
    code: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    pre_close: Decimal
    volume: int
    amount: Decimal
    change_pct: Optional[Decimal] = None
    is_limit_up: bool

    class Config:
        from_attributes = True


class AuctionDataOut(BaseModel):
    code: str
    trade_date: date
    price: Decimal
    pre_close: Decimal
    auction_change_pct: Decimal
    auction_volume: int
    auction_amount: Decimal
    trend: Optional[int] = None

    class Config:
        from_attributes = True


class StrategyResultOut(BaseModel):
    id: int
    strategy_name: str
    trade_date: date
    code: str
    name: str
    auction_amount: Optional[Decimal] = None
    auction_change_pct: Optional[Decimal] = None
    recent_limit_up_date: Optional[date] = None
    pullback_pct: Optional[Decimal] = None
    circulating_market_cap: Optional[Decimal] = None
    trend: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    trade_date: date


class SyncResponse(BaseModel):
    stocks: int = 0
    klines: int = 0
    auctions: int = 0


class StrategyRunRequest(BaseModel):
    trade_date: date
    strategy_text: str = "近5日有涨停，近3日回调超过5%，今日9.25分前竞价抢筹，竞价金额大于1000万，流通市值大于50亿小于300亿，非科创，非创业板，非北交所，非ST"
    strategy_name: str = "竞价低吸"


class ConditionStep(BaseModel):
    label: str
    count: int


class StrategyRunResponse(BaseModel):
    strategy_name: str
    trade_date: str
    conditions: list[ConditionStep]
    count: int
    results: list[dict]


class StrategyResultResponse(BaseModel):
    trade_date: date
    strategy_name: str
    count: int
    results: list[StrategyResultOut]
