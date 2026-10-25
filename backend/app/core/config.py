import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AthletiQ"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./athletiq.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_fallback_key_for_dev")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

settings = Settings()
