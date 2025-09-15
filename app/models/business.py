from typing import List, Optional
from pydantic import BaseModel, Field

class Business(BaseModel):
    id: str
    name: str
    description: str
    categories: List[str] = []
    location: Optional[str] = None
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