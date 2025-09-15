from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.tracking_service import TrackingService, InteractionCreate
from app.models.schemas import BusinessResponse

router = APIRouter()

# This would be initialized in main.py and passed via dependency injection
tracking_service = None

@router.post("/interactions")
async def track_interaction(interaction: InteractionCreate):
    """
    Track a user interaction
    """
    try:
        success = await tracking_service.track_interaction(interaction)
        if success:
            return {"message": "Interaction tracked successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to track interaction")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interactions")
async def get_interactions(user_id: Optional[int] = None, session_id: Optional[str] = None):
    """
    Get interactions for a user or session
    """
    try:
        interactions = await tracking_service.get_user_interactions(user_id, session_id)
        return {"interactions": interactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/popular-businesses", response_model=List[BusinessResponse])
async def get_popular_businesses(limit: int = 10):
    """
    Get popular businesses based on interaction data
    """
    try:
        businesses = await tracking_service.get_popular_businesses(limit)
        return businesses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))