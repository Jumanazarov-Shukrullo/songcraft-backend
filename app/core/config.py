"""Application configuration with proxy support for OpenAI API"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "SongCraft"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Personalized Song Generation Platform"
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # OpenAI Configuration with Proxy Support
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")  # Custom base URL (e.g., reverse proxy)
    OPENAI_PROXY_URL: Optional[str] = Field(default=None, env="OPENAI_PROXY_URL")  # HTTP/HTTPS proxy URL
    
    # Suno AI (for music generation)
    SUNO_API_KEY: str = Field(..., env="SUNO_API_KEY")
    SUNO_API_URL: str = Field(default="https://api.suno.ai", env="SUNO_API_URL")
    
    # Lemon Squeezy Payment Processing
    LEMONSQUEEZY_API_KEY: str = Field(..., env="LEMONSQUEEZY_API_KEY")
    LEMONSQUEEZY_STORE_ID: str = Field(..., env="LEMONSQUEEZY_STORE_ID")
    LEMONSQUEEZY_WEBHOOK_SECRET: str = Field(..., env="LEMONSQUEEZY_WEBHOOK_SECRET")
    LEMONSQUEEZY_API_URL: str = Field(default="https://api.lemonsqueezy.com/v1", env="LEMONSQUEEZY_API_URL")
    LEMONSQUEEZY_PRODUCT_ID_AUDIO: str = Field(..., env="LEMONSQUEEZY_PRODUCT_ID_AUDIO")
    LEMONSQUEEZY_PRODUCT_ID_VIDEO: str = Field(..., env="LEMONSQUEEZY_PRODUCT_ID_VIDEO")
    
    # Email SMTP Configuration
    SMTP_HOST: str = Field(..., env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: str = Field(..., env="SMTP_USERNAME")
    SMTP_PASSWORD: str = Field(..., env="SMTP_PASSWORD")
    SMTP_USE_TLS: bool = Field(default=True, env="SMTP_USE_TLS")
    FROM_EMAIL: str = Field(default="noreply@songcraft.app", env="FROM_EMAIL")
    FROM_NAME: str = Field(default="SongCraft", env="FROM_NAME")
    
    # MinIO File Storage
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(..., env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(..., env="MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME: str = Field(..., env="MINIO_BUCKET_NAME")
    MINIO_SECURE: bool = Field(default=False, env="MINIO_SECURE")  # Use HTTPS
    
    # CORS
    ALLOWED_HOSTS: list[str] = Field(default=["http://localhost:3000"], env="ALLOWED_HOSTS")
    
    # Application URLs
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    BACKEND_URL: str = Field(default="http://localhost:8000", env="BACKEND_URL")
    
    # File Processing
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    MAX_FILES_PER_UPLOAD: int = Field(default=30, env="MAX_FILES_PER_UPLOAD")
    ALLOWED_IMAGE_TYPES: list[str] = Field(default=["image/jpeg", "image/png", "image/webp"])
    
    # Pricing
    AUDIO_PRICE: int = Field(default=1900, env="AUDIO_PRICE")  # $19.00 in cents
    VIDEO_PRICE: int = Field(default=2900, env="VIDEO_PRICE")  # $29.00 in cents
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Development
    DEBUG: bool = Field(default=False, env="DEBUG")
    TESTING: bool = Field(default=False, env="TESTING")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 