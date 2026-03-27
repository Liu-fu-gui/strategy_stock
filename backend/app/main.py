"""策略选股系统 - FastAPI 入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import data, stock, strategy, settings as settings_api
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.data_syncer import ensure_market_cap_cache
from app.services.eastmoney_client import eastmoney_client
from app.services.xtick_client import xtick_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    await init_db()
    await ensure_market_cap_cache()
    start_scheduler()
    yield
    # 关闭时
    stop_scheduler()
    await eastmoney_client.close()
    await xtick_client.close()


app = FastAPI(
    title=settings.APP_TITLE,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(data.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(strategy.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "策略选股系统", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
