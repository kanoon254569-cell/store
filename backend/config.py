"""Configuration Management"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = "ecommerce_db"
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    REQUESTS_PER_MINUTE: int = 60
    PURCHASE_LIMIT_PER_MINUTE: int = 5  # ป้องกัน double purchase
    
    # Server
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"

settings = Settings()
