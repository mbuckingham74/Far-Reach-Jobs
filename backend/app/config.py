from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "far_reach_jobs"
    mysql_user: str = "far_reach_jobs"
    mysql_password: str = ""

    # Auth
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""

    # App
    app_url: str = "http://localhost:8000"
    environment: str = "development"

    @property
    def database_url(self) -> str:
        return f"mysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
