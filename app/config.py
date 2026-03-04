from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/resto_db"
    AES_ENCRYPTION_KEY: str = "0" * 64
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_EXPIRY_MINUTES: int = 1440
    OTP_EXPIRY_MINUTES: int = 5

    @model_validator(mode="after")
    def ensure_async_driver(self) -> "Settings":
        if self.DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in self.DATABASE_URL:
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


settings = Settings()
