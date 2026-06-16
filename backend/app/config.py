from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = ""
    # Tägliches Free-Tier-Limit (Requests/Tag) – nur zur Anzeige, anpassbar via .env
    gemini_daily_limit: int = 1500

    # JWT
    jwt_secret_key: str = "change_me_in_production"
    jwt_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
