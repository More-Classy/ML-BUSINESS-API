# app/utils/helpers.py
from typing import List, Dict, Any
import json
from datetime import datetime
import re

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def format_business_data(business_data: Dict) -> Dict:
    """Format business data for API response"""
    return {
        "id": business_data.get("businessid"),
        "name": business_data.get("businessname"),
        "description": business_data.get("description"),
        "location": business_data.get("location"),
        "latitude": business_data.get("latitude"),
        "longitude": business_data.get("longitude"),
        "rating": float(business_data.get("rating", 0)),
        "review_count": business_data.get("reviewcount", 0),
        "price_level": business_data.get("pricelevel"),
        "photos": []  # Would be populated from another query
    }

def calculate_relevance_score(business: Dict, user_prefs: Dict) -> float:
    """Calculate relevance score for a business based on user preferences"""
    score = 0.0
    
    # Base score from rating
    score += float(business.get("rating", 0)) * 0.2
    
    # Score from review count (logarithmic)
    review_count = business.get("review_count", 0)
    if review_count > 0:
        score += min(0.2, 0.1 * (1 + (review_count ** 0.3)))
    
    # TODO: Add more relevance factors based on user preferences
    # For example: category matching, location proximity, price range matching
    
    return round(score, 2)

def serialize_json(data: Any) -> str:
    """Serialize data to JSON with datetime support"""
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)
    
    return json.dumps(data, cls=DateTimeEncoder)