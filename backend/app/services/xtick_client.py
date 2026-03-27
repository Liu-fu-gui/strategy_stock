"""xtick API 客户端 - 带重试和错误处理"""
import asyncio
import logging
import httpx
from datetime import date
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class XtickApiError(Exception):
    """xtick API 业务错误(额度用完/无权限等)"""
    pass


class XtickClient:

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60)

    @property
    def base_url(self) -> str:
        return settings.XTICK_BASE_URL.rstrip("/")

    @property
    def token(self) -> str:
        return settings.XTICK_TOKEN

    async def close(self):
        await self.client.aclose()

    async def _get_with_retry(self, url: str, params: dict, retries: int = 3) -> httpx.Response:
        for attempt in range(retries):
            try:
                resp = await self.client.get(url, params=params)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt < retries - 1:
                    wait = 2 * (attempt + 1)
                    logger.warning(f"请求失败 (第{attempt+1}次), {wait}秒后重试: {e}")
                    await asyncio.sleep(wait)
                else:
                    raise

    def _check_response(self, data) -> list:
        """校验API返回, 如果是错误响应则抛异常, 正常则返回列表数据"""
        if isinstance(data, dict):
            code = data.get("code")
            if code == -1:
                msg = data.get("message", "未知错误")
                raise XtickApiError(f"xtick API 错误: {msg}")
            # 有些接口返回 {data: [...]}
            inner = data.get("data")
            if isinstance(inner, list):
                return inner
            return []
        if isinstance(data, list):
            return data
        return []

    # ---------- 股票列表 ----------
    async def get_stock_list(self, symbol: str = "all") -> list[dict]:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/stockinfo", {"symbol": symbol, "token": self.token}
        )
        return self._check_response(resp.json())

    # ---------- 日K线 ----------
    async def get_daily_kline(self, code: str, start_date: date, end_date: date) -> list[dict]:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/kline/market",
            {"type": 1, "code": code, "period": "1d", "fq": "none",
             "startDate": start_date.isoformat(), "endDate": end_date.isoformat(), "token": self.token},
        )
        return self._check_response(resp.json())

    async def get_all_daily_kline(self, trade_date: date) -> list[dict]:
        return await self.get_daily_kline("all", trade_date, trade_date)

    # ---------- 竞价数据(实时) ----------
    async def get_realtime_auction(self, code: str = "all", option: Optional[str] = None) -> list[dict]:
        params = {"type": 1, "code": code, "token": self.token}
        if option:
            params["option"] = option
        resp = await self._get_with_retry(f"{self.base_url}/doc/bid/time", params)
        return self._check_response(resp.json())

    # ---------- 竞价数据(历史) ----------
    async def get_history_auction(self, code: str, start_date: date, end_date: date, seq: int = 0) -> list[dict]:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/bid/history",
            {"type": 1, "code": code, "seq": seq,
             "startDate": start_date.isoformat(), "endDate": end_date.isoformat(), "token": self.token},
        )
        return self._check_response(resp.json())

    async def get_all_history_auction(self, trade_date: date) -> list[dict]:
        return await self.get_history_auction("all", trade_date, trade_date)

    # ---------- 量化因子(含流通市值) ----------
    async def get_quant_data(self, fields: str = "x024,x025") -> dict:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/quant/data",
            {"type": 1, "field": fields, "token": self.token},
        )
        data = resp.json()
        if isinstance(data, dict) and data.get("code") == -1:
            raise XtickApiError(f"xtick API 错误: {data.get('message', '')}")
        return data

    # ---------- 实时Tick ----------
    async def get_realtime_tick(self, code: str = "all") -> list[dict]:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/tick/time",
            {"type": 1, "code": code, "token": self.token},
        )
        return self._check_response(resp.json())

    # ---------- 历史Tick ----------
    async def get_history_tick(self, code: str, start_date: date, end_date: date) -> list[dict]:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/tick/history",
            {"type": 1, "code": code, "startDate": start_date.isoformat(),
             "endDate": end_date.isoformat(), "token": self.token},
        )
        return self._check_response(resp.json())

    # ---------- 竞价详情 ----------
    async def get_auction_detail(self, code: str, trade_date: date) -> list[dict]:
        resp = await self._get_with_retry(
            f"{self.base_url}/doc/bid/detail",
            {"type": 1, "code": code, "tradeDate": trade_date.isoformat(), "token": self.token},
        )
        return self._check_response(resp.json())


xtick_client = XtickClient()
