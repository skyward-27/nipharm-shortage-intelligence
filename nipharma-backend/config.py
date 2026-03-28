"""
Configuration settings for Nipharma Backend
Loads from environment variables and .env file
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings"""

    # API Keys
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY")

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Groq Configuration
    GROQ_MODEL: str = "mixtral-8x7b-32768"
    GROQ_TEMPERATURE: float = 0.7
    GROQ_MAX_TOKENS: int = 512

    # News API Configuration
    NEWS_API_URL: str = "https://newsapi.org/v2/everything"
    NEWS_API_TIMEOUT: int = 10
    NEWS_DEFAULT_LIMIT: int = 10
    NEWS_MAX_LIMIT: int = 50

    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    # Application Info
    APP_NAME: str = "Nipharma API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Pharmaceutical Supply Chain Intelligence Backend"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.ENVIRONMENT.lower() == "production"

    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development"""
        return cls.ENVIRONMENT.lower() == "development"

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate configuration settings.
        Returns: (is_valid, list_of_errors)
        """
        errors = []

        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY not configured")

        if not cls.NEWS_API_KEY:
            errors.append("NEWS_API_KEY not configured")

        if cls.PORT < 1 or cls.PORT > 65535:
            errors.append(f"Invalid PORT: {cls.PORT}")

        if cls.GROQ_TEMPERATURE < 0 or cls.GROQ_TEMPERATURE > 2:
            errors.append(f"Invalid GROQ_TEMPERATURE: {cls.GROQ_TEMPERATURE}")

        if cls.GROQ_MAX_TOKENS < 1:
            errors.append(f"Invalid GROQ_MAX_TOKENS: {cls.GROQ_MAX_TOKENS}")

        return len(errors) == 0, errors

    @classmethod
    def log_config(cls) -> None:
        """Log current configuration (without sensitive data)"""
        print("=" * 50)
        print("Nipharma Backend Configuration")
        print("=" * 50)
        print(f"Environment: {cls.ENVIRONMENT}")
        print(f"Host: {cls.HOST}:{cls.PORT}")
        print(f"Version: {cls.APP_VERSION}")
        print(f"Groq Model: {cls.GROQ_MODEL}")
        print(f"Groq Temperature: {cls.GROQ_TEMPERATURE}")
        print(f"Groq Max Tokens: {cls.GROQ_MAX_TOKENS}")
        print(f"News API Limit: {cls.NEWS_DEFAULT_LIMIT}/{cls.NEWS_MAX_LIMIT}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("=" * 50)


# Create settings instance
settings = Settings()
