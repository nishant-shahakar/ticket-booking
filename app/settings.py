"""
Application settings and configuration.
Load from environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration."""

    # Database
    database_url: str
    database_echo: bool = False

    # App
    app_name: str = "Ticket Booking System"
    app_version: str = "0.1.0"
    debug: bool = False

    # Hold expiry
    hold_expiry_minutes: int = 5

    # Background scheduler
    scheduler_enabled: bool = True
    scheduler_hold_cleanup_interval_seconds: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
