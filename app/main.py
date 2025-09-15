# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.services.database_service import create_db_service, get_db_service
from app.core.config import settings
from app.database.connection import database
from app.api.v1.api import api_router
from app.services.onboarding_service import AIOnboardingService
from app.services.recommendation_service import RecommendationService, set_recommendation_service

from app.services.tracking_service import TrackingService
from app.services.dialogflow_service import DialogflowService
from app.utils.logging import setup_logging
from app.utils.cache import cache

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global service instances
services = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize all services
    logger.info("Starting up application...")
    
    try:
        # Initialize database connection
        await database.connect()
        logger.info("Database connected successfully")

        # Initialize DatabaseService with connected pool
        await create_db_service(database.pool)
        logger.info("DatabaseService initialized")
        
        # Initialize Redis cache
        # await cache.connect()
        # logger.info("Cache initialized")
        database_service = get_db_service()
        # services["recommendation"] = RecommendationService(database_service)
        
        # Initialize services
        services["onboarding"] = AIOnboardingService()
        services["recommendation"] = RecommendationService(database_service)

        set_recommendation_service(services["recommendation"])

        services["tracking"] = TrackingService(database.pool)
        services["dialogflow"] = DialogflowService()

        # preload businesses from database
        logger.info("Preloading businesses from database...")
        businesses = await services["recommendation"].get_all_businesses()

        logger.info(f"Successfully preloaded {len(businesses)} businesses from database")
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Shutting down application...")
    await database.disconnect()
    logger.info("Application shutdown complete")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Centralized ML Hub for Business Recommendations, AI Support, and Business Onboarding",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "ML Hub API",
        "version": "1.0.0",
        "docs": "/docs",
        "services": {
            "onboarding": "Available",
            "recommendations": "Available", 
            "tracking": "Available",
            "dialogflow": "Available" if settings.DIALOGFLOW_PROJECT_ID else "Disabled"
        }
    }