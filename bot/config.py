from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, HttpUrl, validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Обязательно
    BOT_TOKEN: SecretStr
    
    # Опционально для вебхука
    WEBHOOK_BASE_URL: HttpUrl | None = None
    WEBHOOK_SECRET: SecretStr | None = None
    WEBHOOK_PATH: str = "/webhook"
    
    # Приложение
    PORT: int = Field(default=8080, ge=1024, le=65535)
    
    @property
    def webhook_url(self) -> str | None:
        if self.WEBHOOK_BASE_URL:
            return f"{self.WEBHOOK_BASE_URL}{self.WEBHOOK_PATH}"
        return None


settings = Settings()
