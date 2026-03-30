from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vascora"
    postgres_user: str = "vascora"
    postgres_password: str = "change_me"

    sentiment_source: str = "devvit_webhook"
    devvit_webhook_token: str = "replace_with_shared_secret"
    ingest_api_token: str = "change_me_ingest_token"

    api_base_url: str = "http://localhost:8000"
    burlington_lat: float = 43.3255
    burlington_lng: float = -79.7990
    market_radius_km: float = 35.0
    google_places_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
