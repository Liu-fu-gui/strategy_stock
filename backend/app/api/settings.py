"""系统设置接口"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["系统设置"])


class EnvSettings(BaseModel):
    database_url: str
    redis_url: str
    xtick_base_url: str
    xtick_token: str
    xtick_ws_token: str


@router.get("/env", summary="获取环境配置")
async def get_env_settings():
    from app.core.config import settings
    return {
        "database_url": settings.DATABASE_URL,
        "redis_url": settings.REDIS_URL,
        "xtick_base_url": settings.XTICK_BASE_URL,
        "xtick_token": settings.XTICK_TOKEN,
        "xtick_ws_token": settings.XTICK_WS_TOKEN,
    }


@router.post("/env", summary="更新环境配置")
async def update_env_settings(data: EnvSettings):
    import os
    from app.core.config import settings

    env_path = os.path.join(os.path.dirname(__file__), "../../.env")

    content = f"""DATABASE_URL={data.database_url}
DATABASE_URL_SYNC={data.database_url.replace('asyncpg', 'psycopg2')}
REDIS_URL={data.redis_url}
XTICK_BASE_URL={data.xtick_base_url}
XTICK_TOKEN={data.xtick_token}
XTICK_WS_TOKEN={data.xtick_ws_token}
"""

    with open(env_path, 'w') as f:
        f.write(content)

    settings.DATABASE_URL = data.database_url
    settings.DATABASE_URL_SYNC = data.database_url.replace('asyncpg', 'psycopg2')
    settings.REDIS_URL = data.redis_url
    settings.XTICK_BASE_URL = data.xtick_base_url
    settings.XTICK_TOKEN = data.xtick_token
    settings.XTICK_WS_TOKEN = data.xtick_ws_token

    return {"success": True, "message": "配置已保存，当前进程已即时生效"}
