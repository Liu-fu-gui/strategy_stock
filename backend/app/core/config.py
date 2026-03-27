from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://stock:stock123456@10.100.20.206:5432/app"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://stock:stock123456@10.100.20.206:5432/app"

    # Redis
    REDIS_URL: str = "redis://:redis123456@10.100.20.206:6380/0"

    # xtick API
    XTICK_BASE_URL: str = "http://api.xtick.top"
    XTICK_TOKEN: str = "0d8aa771dd0a0e33624e1546d13c3eb6"

    # 应用
    APP_TITLE: str = "策略选股系统"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
