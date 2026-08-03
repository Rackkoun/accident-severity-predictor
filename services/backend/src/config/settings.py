from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings loaded from .env.backend or environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env.backend",
        # case_sensitive=True,
        extra="ignore",
    )

    # api_admin_username: str = Field(default="")
    admin_password: str = Field(default="")
    # api_admin_role: str = Field(default="admin")

    # api_user_username: str = Field(default="")
    user_password: str = Field(default="")
    # api_user_role:  = Field(default="user")

    # def get_admin(self) -> UserCredentials:
    #     return UserCredentials(
    #         username=self.api_admin_username,
    #         password_hash=self.api_admin_password_hash,
    #         role=self.api_admin_role,
    #     )

    # def get_user(self) -> UserCredentials:
    #     return UserCredentials(
    #         username=self.api_user_username,
    #         password_hash=self.api_user_password_hash,
    #         role=self.api_user_role,
    #     )


@lru_cache
def get_settings() -> Settings:
    return Settings()
