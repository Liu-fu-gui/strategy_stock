"""东方财富公开行情接口客户端"""
from datetime import date, datetime

import httpx


class EastmoneyClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={
                "Referer": "https://quote.eastmoney.com/",
                "User-Agent": "Mozilla/5.0",
            },
        )

    async def close(self):
        await self.client.aclose()

    async def get_limit_up_pool(self, trade_date: date) -> list[dict]:
        ts_ms = int(datetime.combine(trade_date, datetime.min.time()).timestamp() * 1000)
        resp = await self.client.get(
            "https://push2ex.eastmoney.com/getTopicZTPool",
            params={
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "dpt": "wz.ztzt",
                "Pageindex": 0,
                "pagesize": 500,
                "sort": "fbt:asc",
                "date": trade_date.strftime("%Y%m%d"),
                "_": ts_ms,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or {}
        pool = data.get("pool") or []
        if not isinstance(pool, list):
            return []
        return pool


eastmoney_client = EastmoneyClient()
