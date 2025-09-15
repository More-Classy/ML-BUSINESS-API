from typing import List, Optional, Dict, Any
from datetime import datetime
from app.database.connection import database
from app.models.schemas import BusinessResponse
from pydantic import BaseModel, Field
from enum import Enum

# Define the missing schemas locally since they don't exist in schemas.py
class InteractionType(str, Enum):
    VIEW = "view"
    CLICK = "click"
    PURCHASE = "purchase"
    SEARCH = "search"
    FAVORITE = "favorite"

class InteractionCreate(BaseModel):
    user_id: Optional[int] = Field(None, description="User ID if available")
    session_id: str = Field(..., description="Session identifier")
    business_id: Optional[str] = Field(None, description="Business ID if applicable")
    interaction_type: InteractionType = Field(..., description="Type of interaction")
    element_id: Optional[str] = Field(None, description="UI element identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional interaction data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Interaction timestamp")

class TrackingService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.interactions = []  # In-memory storage for now
    
    async def track_interaction(self, interaction: InteractionCreate) -> bool:
        """
        Track a user interaction
        """
        try:
            # For now, store in memory
            self.interactions.append(interaction.dict())
            
            # In a real implementation, you'd save to database:
            # query = "INSERT INTO interactions (...) VALUES (...)"
            # await self.db_pool.execute(query, ...)
            
            print(f"Tracked interaction: {interaction.interaction_type} for session {interaction.session_id}")
            return True
        except Exception as e:
            print(f"Error tracking interaction: {e}")
            return False
    
    async def get_user_interactions(self, user_id: Optional[int] = None, session_id: Optional[str] = None) -> List[InteractionCreate]:
        """
        Get interactions for a user or session
        """
        try:
            if user_id:
                return [InteractionCreate(**i) for i in self.interactions if i.get('user_id') == user_id]
            elif session_id:
                return [InteractionCreate(**i) for i in self.interactions if i.get('session_id') == session_id]
            else:
                return [InteractionCreate(**i) for i in self.interactions]
        except Exception as e:
            print(f"Error getting interactions: {e}")
            return []
    
    async def get_popular_businesses(self, limit: int = 10) -> List[BusinessResponse]:
        """
        Get popular businesses based on interaction data
        """
        try:
            # Simple popularity calculation based on view counts
            business_views = {}
            for interaction in self.interactions:
                if interaction.interaction_type in [InteractionType.VIEW, InteractionType.CLICK] and interaction.business_id:
                    business_views[interaction.business_id] = business_views.get(interaction.business_id, 0) + 1
            
            # Sort by view count
            popular_business_ids = sorted(business_views.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            # In a real implementation, you'd fetch business details from database
            # For now, return mock data or integrate with your recommendation service
            return []
            
        except Exception as e:
            print(f"Error getting popular businesses: {e}")
            return []