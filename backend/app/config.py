from pydantic_settings import BaseSettings
from pydantic import model_validator
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

    # Admin
    admin_username: str = "admin"
    admin_password: str = "changeme"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """Ensure secret_key is set properly in non-development environments."""
        weak_keys = {"change-me-in-production", "", "secret", "changeme"}
        if self.environment != "development" and self.secret_key in weak_keys:
            raise ValueError(
                f"SECRET_KEY must be set to a secure value in {self.environment} environment. "
                "Generate one with: openssl rand -hex 32"
            )
        return self

    @property
    def database_url(self) -> str:
        return (
            f"mysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
