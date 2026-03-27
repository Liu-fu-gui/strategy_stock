from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Date, DateTime, Numeric, BigInteger, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Stock(Base):
    """股票基础信息 - 匹配现有数据库表结构"""
    __tablename__ = "stocks"
    __table_args__ = {"extend_existing": True}

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(20))
    market: Mapped[str] = mapped_column(String(10))
    list_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    circulating_market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    @property
    def board(self) -> str:
        """根据代码推断板块"""
        if self.code.startswith("688"):
            return "kcb"
        elif self.code.startswith("3"):
            return "cyb"
        elif self.code.startswith(("4", "8")):
            return "bj"
        return "main"

    @property
    def is_st(self) -> bool:
        return "ST" in (self.name or "").upper()


class DailyKline(Base):
    """日K线数据"""
    __tablename__ = "daily_klines"
    __table_args__ = (
        Index("ix_kline_code_date", "code", "trade_date", unique=True),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    high: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    low: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    close: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    pre_close: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    volume: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    is_limit_up: Mapped[bool] = mapped_column(Boolean, default=False)


class AuctionData(Base):
    """竞价数据"""
    __tablename__ = "auction_data"
    __table_args__ = (
        Index("ix_auction_code_date", "code", "trade_date", unique=True),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    pre_close: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    auction_change_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    auction_volume: Mapped[int] = mapped_column(BigInteger)
    auction_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    unmatched_volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    unmatched_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    trend: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class StrategyResult(Base):
    """策略筛选结果"""
    __tablename__ = "strategy_results"
    __table_args__ = (
        Index("ix_result_strategy_date", "strategy_name", "trade_date"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(50), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(20))
    auction_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    auction_change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    recent_limit_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pullback_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    circulating_market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)
    trend: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, nullable=True)


class StrategyTemplate(Base):
    """策略模板"""
    __tablename__ = "strategy_templates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    content: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
