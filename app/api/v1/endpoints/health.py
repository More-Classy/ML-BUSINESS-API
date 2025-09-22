from fastapi import APIRouter
from app.database.connection import database
from app.models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint to verify API and database connectivity"""
    try:
        await database.fetch_all("SELECT 1")
        return HealthResponse(
            status="healthy",
            database="connected",
            services={
                "onboarding": "available",
                "recommendations": "available",
                "tracking": "available",
                "dialogflow": "available"
            }
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database="disconnected",
            services={
                "onboarding": "unavailable",
                "recommendations": "unavailable",
                "tracking": "unavailable",
                "dialogflow": "unavailable"
            }
        )

@router.get("/version", tags=["Health"])
async def version():
    """Get API version information"""
    return {
        "name": "ML Hub API",
        "version": "1.0.0",
        "description": "Centralized ML Hub for Business Recommendations and AI Support"
    }
