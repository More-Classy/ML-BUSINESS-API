from fastapi import APIRouter, HTTPException,  Request, Response
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid
from app.models.schemas import (
    PreferenceRecommendationRequest,
    BehaviorRecommendationRequest,
    BehaviorTrackingRequest,
    BusinessResponse,
    BehaviorTrackingResponse,
    RecommendationResponse
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
async def get_recommendations_by_behavior(
    request: Request,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 10
):
    try:
        # Get session ID from cookie if not provided
        if not user_id and not session_id:
            session_id = request.cookies.get("session_id")
        
        businesses = await get_recommendation_service().recommend_based_on_behavior(
            user_id, session_id
        )
        
        return RecommendationResponse(
            businesses=businesses[:limit],
            source="behavior_based",
            confidence=0.7 if user_id or session_id else 0.6
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track-behavior", response_model=BehaviorTrackingResponse)
async def track_user_behavior(
    request: Request,
    response: Response,
    tracking_request: BehaviorTrackingRequest
):
    try:
        # Generate or get session ID for unauthenticated users
        session_id = tracking_request.session_id
        if not tracking_request.user_id and not session_id:
            # Generate new session ID for unauthenticated user
            session_id = str(uuid.uuid4())
            # Set session cookie
            response.set_cookie(
                key="session_id", 
                value=session_id, 
                max_age=30*24*60*60,  # 30 days
                httponly=True
            )
        
        # Track behavior and get recommendations
        similar_businesses, recommended_businesses = await get_recommendation_service().track_user_behavior(
            tracking_request.user_id,
            session_id,
            tracking_request.business_id,
            tracking_request.action
        )
        
        return BehaviorTrackingResponse(
            message="Behavior tracked successfully",
            similar_businesses=similar_businesses,
            recommended_businesses=recommended_businesses
        )
        
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
