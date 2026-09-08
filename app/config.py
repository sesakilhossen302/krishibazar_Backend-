import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Krishi Bazaar Backend API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./krishibazar.db"
    SECRET_KEY: str = "KRISHI_BAZAAR_SUPER_SECRET_KEY_2026_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200

    # Gmail SMTP Configuration for sending OTPs
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # Your Gmail address (e.g. sakil.krishibazar@gmail.com)
    SMTP_PASSWORD: str = ""  # Google App Password (16 characters)
    SMTP_FROM_NAME: str = "কৃষিবাজার (Krishi Bazaar)"
    SMTP_FROM_EMAIL: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

