"""WebSocket 竞价数据接收器 - 连接 xtick WebSocket 实时接收竞价推送"""
import asyncio
import gzip
import io
import json
import logging
import zipfile
import urllib.parse
from datetime import date, datetime

from app.core.config import settings
from app.core.database import async_session
from app.models.stock import AuctionData
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)

# 最新竞价数据缓存 (code -> dict)
auction_cache: dict[str, dict] = {}
# 接收状态
ws_connected = False
last_receive_time: str = ""
receive_count: int = 0


def _decompress(data: bytes) -> dict:
    """解压 WebSocket 推送的二进制数据"""
    if data[:2] == b'\x1f\x8b':  # GZIP
        decompressed = gzip.decompress(data)
        return json.loads(decompressed)
    elif data[:2] == b'\x50\x4b':  # ZIP
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            name = zf.namelist()[0]
            return json.loads(zf.read(name))
    else:
        return json.loads(data)


def _build_ws_url() -> str:
    """构建 WebSocket 连接 URL"""
    user_info = json.dumps({
        "token": settings.XTICK_TOKEN,
        "authCodes": ["bid.1"],
    })
    user_encoded = urllib.parse.quote(user_info)
    return f"ws://ws.xtick.top/ws/{user_encoded}"


async def _save_auction_batch(records: list[dict], trade_date: date):
    """批量保存竞价数据到数据库"""
    if not records:
        return
    rows = []
    for item in records:
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
        return

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
    logger.info(f"保存竞价数据 {len(rows)} 条")


async def start_ws_receiver():
    """启动 WebSocket 接收, 9:15~9:25 期间持续接收竞价数据"""
    global ws_connected, last_receive_time, receive_count, auction_cache

    try:
        import websockets
    except ImportError:
        logger.error("需要安装 websockets: pip install websockets")
        return

    url = _build_ws_url()
    logger.info(f"连接 WebSocket: ws://ws.xtick.top/ws/...")

    save_buffer: list[dict] = []
    today = date.today()

    try:
        async with websockets.connect(url, max_size=5 * 1024 * 1024) as ws:
            ws_connected = True
            logger.info("WebSocket 已连接, 等待竞价数据推送...")

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=120)
                except asyncio.TimeoutError:
                    logger.info("WebSocket 120秒无数据, 可能竞价已结束")
                    break

                if isinstance(msg, bytes):
                    try:
                        packet = _decompress(msg)
                    except Exception as e:
                        logger.warning(f"解压失败: {e}")
                        continue
                else:
                    try:
                        packet = json.loads(msg)
                    except:
                        continue

                period = packet.get("period", "")
                if period != "bid":
                    continue

                data_list = packet.get("data", [])
                if not isinstance(data_list, list):
                    continue

                # 更新内存缓存
                for item in data_list:
                    code = item.get("code", "")
                    if code:
                        auction_cache[code] = item
                        save_buffer.append(item)

                receive_count += len(data_list)
                last_receive_time = datetime.now().strftime("%H:%M:%S")

                # 每积累 500 条写一次数据库
                if len(save_buffer) >= 500:
                    await _save_auction_batch(save_buffer, today)
                    save_buffer.clear()

    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
    finally:
        # 写入剩余数据
        if save_buffer:
            await _save_auction_batch(save_buffer, today)
            save_buffer.clear()
        ws_connected = False
        logger.info(f"WebSocket 断开, 共接收 {receive_count} 条, 缓存 {len(auction_cache)} 只")


async def save_final_auction():
    """将内存中最终的竞价数据全量写入数据库(9:25后调用)"""
    if not auction_cache:
        logger.warning("竞价缓存为空, 无数据可保存")
        return 0
    records = list(auction_cache.values())
    await _save_auction_batch(records, date.today())
    logger.info(f"最终竞价数据已保存: {len(records)} 只")
    return len(records)


def get_ws_status() -> dict:
    """获取 WebSocket 接收状态"""
    return {
        "connected": ws_connected,
        "last_receive_time": last_receive_time,
        "receive_count": receive_count,
        "cache_size": len(auction_cache),
    }
