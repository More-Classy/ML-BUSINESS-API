from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel, Field
from app.models.schemas import (
    PreferenceRecommendationRequest,
    BehaviorRecommendationRequest,
    BehaviorTrackingRequest,
    BusinessResponse
)
from app.services.recommendation_service import get_recommendation_service

router = APIRouter()

class RecommendationResponse(BaseModel):
    businesses: List[BusinessResponse] = Field(..., description="List of recommended businesses")
    source: str = Field(..., description="Recommendation source algorithm")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")

@router.post("/preferences", response_model=RecommendationResponse)
async def get_recommendations_by_preferences(request: PreferenceRecommendationRequest):
    try:
        businesses = await get_recommendation_service().recommend_based_on_preferences(
            request.preferences
        )
        return RecommendationResponse(
            businesses=businesses[:request.limit],
            source="preference_based",
            confidence=0.8
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/behavior", response_model=RecommendationResponse)
async def get_recommendations_by_behavior(request: BehaviorRecommendationRequest):
    try:
        businesses = await get_recommendation_service().recommend_based_on_behavior(
            request.user_id
        )
        return RecommendationResponse(
            businesses=businesses[:request.limit],
            source="behavior_based",
            confidence=0.7 if request.user_id else 0.6
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track-behavior")
async def track_user_behavior(request: BehaviorTrackingRequest):
    try:
        await get_recommendation_service().track_user_behavior(
            request.user_id, 
            request.business_id, 
            request.action
        )
        return {"message": "Behavior tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/businesses", response_model=List[BusinessResponse])
async def get_all_businesses(limit: int = 20):
    try:
        # Pass limit to database service
        businesses = await get_recommendation_service().get_all_businesses(limit=limit)
        return businesses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
