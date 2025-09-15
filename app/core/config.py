from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API Settings
    GOOGLE_APPLICATION_CREDENTIALS: str
    PROJECT_NAME: str = "ML Hub API"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""
    DATABASE_NAME: str = "more"
    
    # External APIs
    CSHARP_BACKEND_URL: str = "http://197.248.202.79:5080"
    CSHARP_BUSINESS_ENDPOINT: str = "/api/Business/home-listing"
    OPENAI_API_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None
    DIALOGFLOW_PROJECT_ID: Optional[str] = None
    
    # Redis for caching
    REDIS_URL: Optional[str] = "redis://localhost:6379"
    
    # ML Settings
    RECOMMENDATION_MODEL_PATH: str = "./ml_models/recommendation"
    MIN_TRAINING_SAMPLES: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()