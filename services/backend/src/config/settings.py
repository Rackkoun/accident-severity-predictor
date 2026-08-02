import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    api_username: str = "admin"
    api_password_hash: str


@lru_cache
def get_settings() -> Settings:
    return Settings(api_password_hash=os.environ["API_PASSWORD_HASH"])
