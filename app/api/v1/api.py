from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, 
    onboarding, 
    recommendations, 
    # tracking, 
    dialogflow,
    chat
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["AI Onboarding"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
# api_router.include_router(tracking.router, prefix="/tracking", tags=["User Tracking & Preferences"])
api_router.include_router(dialogflow.router, prefix="/support", tags=["AI Support"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])