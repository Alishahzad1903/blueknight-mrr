from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://mrr:mrr@localhost:5432/mrr"
    jwt_secret: str = "dev-secret-change-me"
    log_format: str = "json"

    model_config = {"env_file": ".env"}


settings = Settings()
