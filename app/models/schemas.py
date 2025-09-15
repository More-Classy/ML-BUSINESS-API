from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

# Business schemas
class BusinessBase(BaseModel):
    name: str = Field(..., max_length=100, description="Business name")
    description: str = Field(..., description="Business description")
    location: Optional[str] = Field(None, max_length=100, description="Business location")

class BusinessCreate(BusinessBase):
    pass

class BusinessResponse(BusinessBase):
    id: str
    categories: List[str] = []
    price: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photos: List[str] = []
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(0, ge=0)
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "business_123",
                "name": "Example Restaurant",
                "description": "A fine dining experience",
                "categories": ["RESTAURANTS", "FINE_DINING"],
                "location": "Nairobi",
                "price": 4.5,
                "address": "123 Main Street",
                "city": "Nairobi",
                "country": "Kenya",
                "latitude": -1.2921,
                "longitude": 36.8219,
                "photos": ["photo1.jpg", "photo2.jpg"],
                "rating": 4.7,
                "review_count": 150
            }
        }

# User schemas
class UserBase(BaseModel):
    email: str = Field(..., description="User email")
    name: str = Field(..., max_length=100, description="User name")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="User password")

class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
class PriceRange(str, Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    PREMIUM = "premium"

class UserPreferences(BaseModel):
    interests: List[str] = Field(..., description="List of user interests")
    location: str = Field(..., description="Preferred location for recommendations")
    price_range: Optional[PriceRange] = Field(None, description="Preferred price range")            

class PreferenceRecommendationRequest(BaseModel):
    preferences: UserPreferences
    limit: int = Field(10, ge=1, le=50, description="Number of recommendations")

class BehaviorRecommendationRequest(BaseModel):
    user_id: Optional[int] = Field(None, description="User ID for personalized recommendations")
    limit: int = Field(10, ge=1, le=50, description="Number of recommendations")

class BehaviorTrackingRequest(BaseModel):
    user_id: Optional[int] = Field(None, description="User ID for tracking")
    business_id: str = Field(..., description="Business ID that was interacted with")
    action: str = Field(..., description="Type of interaction (click, view, purchase, etc.)")

# Tracking schemas
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

class InteractionResponse(InteractionCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
# AI Onboarding schemas
class ServiceSuggestionRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100, description="Name of the business")
    industry_hint: Optional[str] = Field(None, description="Optional industry hint")

class ServiceSuggestionResponse(BaseModel):
    suggested_services: List[str] = Field(..., description="AI-suggested services")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")

class BusinessDescriptionRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100, description="Name of the business")
    services: List[str] = Field(..., max_items=4, min_items=1, description="Business services as free text (max 4)")
    location: Optional[str] = Field(None, max_length=100, description="Business location (optional)")
    
    @validator('services')
    def validate_services_count(cls, v):
        if len(v) > 4:
            raise ValueError('Maximum 4 services allowed')
        for service in v:
            if not service.strip():
                raise ValueError('Service cannot be empty')
            if len(service) > 100:
                raise ValueError('Each service must be less than 100 characters')
        return v

class BusinessDescriptionResponse(BaseModel):
    description: str = Field(..., description="AI-generated business description (100-200 words)")
    auto_filled_category: Optional[Dict] = Field(None, description="Automatically determined primary category")
    word_count: int = Field(..., description="Word count of description")

class BusinessCategoriesRequest(BaseModel):
    services: List[str] = Field(..., max_items=4, min_items=1, description="Business services as free text (max 4)")
    
    @validator('services')
    def validate_services_count(cls, v):
        if len(v) > 4:
            raise ValueError('Maximum 4 services allowed')
        for service in v:
            if not service.strip():
                raise ValueError('Service cannot be empty')
            if len(service) > 100:
                raise ValueError('Each service must be less than 100 characters')
        return v

class BusinessCategoriesResponse(BaseModel):
    suggested_categories: List[Dict] = Field(..., description="AI-matched categories from backend")
    suggested_subcategories: List[Dict] = Field(..., description="Relevant subcategories")
    suggested_tags: List[Dict] = Field(..., max_items=10, description="AI-suggested tags (max 10)")
    confidence_score: float = Field(..., ge=0, le=1, description="AI confidence in suggestions")

class BusinessImagesRequest(BaseModel):
    services: List[str] = Field(..., max_items=4, min_items=1, description="Business services as free text (max 4)")
    
    @validator('services')
    def validate_services_count(cls, v):
        if len(v) > 4:
            raise ValueError('Maximum 4 services allowed')
        for service in v:
            if not service.strip():
                raise ValueError('Service cannot be empty')
            if len(service) > 100:
                raise ValueError('Each service must be less than 100 characters')
        return v

class BusinessImagesResponse(BaseModel):
    image_urls: List[str] = Field(..., min_items=2, max_items=2, description="2 stock business images")
    image_descriptions: List[str] = Field(..., description="Descriptions of images")

class ProductSuggestionsRequest(BaseModel):
    services: List[str] = Field(..., max_items=4, min_items=1, description="Business services as free text (max 4)")

class ProductSuggestionsResponse(BaseModel):
    products: List[Dict[str, str]] = Field(..., max_items=3, description="Max 3 AI-generated products")

# Dialogflow schemas
class DialogflowRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")

class DialogflowResponse(BaseModel):
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    intent: str = Field(..., description="Detected intent")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    source: str = Field(..., description="Response source (dialogflow/chatgpt)")

# Health check schema
class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    services: Dict[str, str] = Field(..., description="Individual service statuses")