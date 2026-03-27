"""东方财富公开行情接口客户端"""
from datetime import date, datetime
import logging

import httpx

logger = logging.getLogger(__name__)


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

    @staticmethod
    def _normalize_diff_rows(diff) -> list[dict]:
        if isinstance(diff, list):
            return [item for item in diff if isinstance(item, dict)]
        if isinstance(diff, dict):
            return [item for item in diff.values() if isinstance(item, dict)]
        return []

    async def _get_market_cap_page(self, page_no: int, page_size: int = 100) -> tuple[list[dict], int]:
        resp = await self.client.get(
            "http://push2.eastmoney.com/api/qt/clist/get",
            params={
                "pn": page_no,
                "pz": page_size,
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f12,f20",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return [], 0
        total = data.get("total") or 0
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = 0
        return self._normalize_diff_rows(data.get("diff")), total

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

    async def get_market_caps(self) -> dict[str, float]:
        """获取全市场流通市值 (亿元)"""
        try:
            page_size = 100
            rows, total = await self._get_market_cap_page(1, page_size=page_size)
            if not rows:
                return {}

            total_pages = max(1, (total + page_size - 1) // page_size)
            for page_no in range(2, total_pages + 1):
                page_rows, _ = await self._get_market_cap_page(page_no, page_size=page_size)
                if not page_rows:
                    break
                rows.extend(page_rows)

            result = {}
            for item in rows:
                code = str(item.get("f12") or "").strip()
                cap = item.get("f20")
                if not code or cap in (None, "", 0, "0"):
                    continue
                try:
                    result[code] = float(cap) / 1e8
                except (TypeError, ValueError):
                    continue

            logger.info(f"从东方财富获取市值: {len(result)} 只")
            return result
        except Exception as e:
            logger.error(f"获取东方财富市值失败: {e}")
            return {}


eastmoney_client = EastmoneyClient()
