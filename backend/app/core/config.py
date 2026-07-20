from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://smallworld:smallworld@localhost:5432/smallworld"
    # Procrastinate connects with a plain psycopg DSN (no SQLAlchemy driver prefix).
    procrastinate_database_url: str = "postgresql://smallworld:smallworld@localhost:5432/smallworld"
    session_cookie_name: str = "sw_session"
    session_ttl_hours: int = 24 * 14
    env: str = "development"
    frontend_url: str = "http://localhost:3000"


settings = Settings()
