from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Expense Agent"
    database_url: str = "sqlite:///./expense_agent.db"
    default_user_name: str = "Default User"
    default_currency: str = "JPY"
    timezone: str = "Asia/Tokyo"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="EXPENSE_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
