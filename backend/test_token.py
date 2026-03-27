import asyncio
import httpx

TOKEN = "0d8aa771dd0a0e33624e1546d13c3eb6"
BASE = "http://api.xtick.top"

async def test_permissions():
    client = httpx.AsyncClient(timeout=30)

    tests = [
        ("股票列表", f"{BASE}/doc/stockinfo?symbol=all&token={TOKEN}"),
        ("日K线", f"{BASE}/doc/kline/market?type=1&code=000001&period=1d&fq=none&startDate=2026-03-27&endDate=2026-03-27&token={TOKEN}"),
        ("竞价数据", f"{BASE}/doc/bid/history?type=1&code=000001&seq=0&startDate=2026-03-27&endDate=2026-03-27&token={TOKEN}"),
        ("流通市值", f"{BASE}/doc/quant/data?type=1&field=x025&token={TOKEN}"),
    ]

    print(f"测试 Token: {TOKEN}\n")

    for name, url in tests:
        try:
            resp = await client.get(url)
            data = resp.json()

            if isinstance(data, dict) and data.get("code") == -1:
                print(f"❌ {name}: {data.get('message')}")
            elif isinstance(data, list) and len(data) > 0:
                print(f"✅ {name}: 有权限 (返回 {len(data)} 条)")
            elif isinstance(data, dict) and "data" in data:
                print(f"✅ {name}: 有权限")
            else:
                print(f"⚠️  {name}: 返回格式异常")
        except Exception as e:
            print(f"❌ {name}: 请求失败 - {e}")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_permissions())
