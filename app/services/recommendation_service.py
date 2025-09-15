import requests
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.models.schemas import BusinessResponse, UserPreferences, PriceRange
import json
import random
import time
import logging

logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self, database_service):
        self.database_service = database_service
        self.csharp_backend_url = settings.CSHARP_BACKEND_URL
        self.business_endpoint = settings.CSHARP_BUSINESS_ENDPOINT
        self.cache = {}  # Simple in-memory cache
        self.user_behavior = {}  # Store user behavior in memory

    async def get_all_businesses(self, limit:Optional[int] = None) -> List[BusinessResponse]:
        """Get all businesses from database"""
        try:
            return await self.database_service.get_all_businesses_from_db(limit=limit)

        except Exception as e:
            logger.warning(f"Failed to get businesses from database: {e}")
            # Fallback to mock data
            return self._get_mock_businesses()
    
    def _parse_business_data(self, business_data: Dict) -> Optional[BusinessResponse]:
        """Parse business data from C# API response format"""
        try:
            if not isinstance(business_data, dict):
                return None
            
            # Map C# API fields to our schema based on the actual response
            mapped_data = {}
            
            # Basic fields
            mapped_data['id'] = business_data.get('businessID', '')
            mapped_data['name'] = business_data.get('name', '').strip()
            mapped_data['description'] = business_data.get('description', '').strip()
            mapped_data['address'] = business_data.get('address', '')
            mapped_data['city'] = business_data.get('city', '')
            mapped_data['country'] = business_data.get('country', '')
            mapped_data['latitude'] = business_data.get('latitude')
            mapped_data['longitude'] = business_data.get('longitude')
            
            # Location - combine city and country
            location_parts = []
            if business_data.get('city'):
                location_parts.append(business_data['city'])
            if business_data.get('country'):
                location_parts.append(business_data['country'])
            mapped_data['location'] = ', '.join(location_parts) if location_parts else 'Unknown'
            
            # Categories - extract from subcategories
            categories = set()
            if 'businessSubCategories' in business_data and isinstance(business_data['businessSubCategories'], list):
                for subcat in business_data['businessSubCategories']:
                    if isinstance(subcat, dict) and 'subCategoryName' in subcat:
                        categories.add(subcat['subCategoryName'])
            mapped_data['categories'] = list(categories)
            
            # Price - set a default since it's not in the C# response
            base_price = random.uniform(500, 5000)
            mapped_data['price'] = base_price
            
            # Photos - extract from businessPhotos
            photos = []
            if 'businessPhotos' in business_data and isinstance(business_data['businessPhotos'], list):
                for photo in business_data['businessPhotos']:
                    if isinstance(photo, dict) and 'photoURL' in photo:
                        photos.append(photo['photoURL'])
            mapped_data['photos'] = photos
            
            # Rating and review count - extract from reviewsData
            reviews_data = business_data.get('reviewsData', {})
            if isinstance(reviews_data, dict):
                mapped_data['rating'] = reviews_data.get('rating', 0.0)
                mapped_data['review_count'] = reviews_data.get('count', 0)
            else:
                mapped_data['rating'] = 0.0
                mapped_data['review_count'] = 0
            
            # Ensure all required fields have defaults
            mapped_data.setdefault('categories', [])
            mapped_data.setdefault('photos', [])
            mapped_data.setdefault('review_count', 0)
            mapped_data.setdefault('rating', 0.0)
            
            # Create the business response
            business = BusinessResponse(**mapped_data)
            
            return business
            
        except Exception as e:
            logger.warning(f"Failed to parse business data: {e}")
            return None
    
    def _get_mock_businesses(self) -> List[BusinessResponse]:
        """Generate mock businesses for testing"""
        mock_businesses = [
            BusinessResponse(
                id="business_1",
                name="Nairobi Tech Hub",
                description="A modern co-working space for tech startups and freelancers",
                categories=["TECH", "COWORKING", "OFFICE_SPACE"],
                location="Nairobi, Kenya",
                price=800.0,
                address="123 Tech Street",
                city="Nairobi",
                country="Kenya",
                latitude=-1.2921,
                longitude=36.8219,
                photos=[],
                rating=4.5,
                review_count=45
            ),
            BusinessResponse(
                id="business_2",
                name="Budget Tech Solutions",
                description="Affordable tech gadgets and repair services",
                categories=["TECH", "ELECTRONICS", "REPAIR"],
                location="Nairobi, Kenya",
                price=500.0,
                address="456 Budget Avenue",
                city="Nairobi",
                country="Kenya",
                latitude=-1.2861,
                longitude=36.8172,
                photos=[],
                rating=4.2,
                review_count=32
            ),
            BusinessResponse(
                id="business_3",
                name="Premium Tech Store",
                description="High-end technology products and gadgets",
                categories=["TECH", "ELECTRONICS", "PREMIUM"],
                location="Nairobi, Kenya",
                price=4500.0,
                address="789 Premium Road",
                city="Nairobi",
                country="Kenya",
                latitude=-1.2897,
                longitude=36.8234,
                photos=[],
                rating=4.8,
                review_count=78
            ),
            BusinessResponse(
                id="business_4",
                name="Nairobi Coffee Shop",
                description="Cozy coffee shop with free WiFi",
                categories=["FOOD", "COFFEE", "CAFE"],
                location="Nairobi, Kenya",
                price=350.0,
                address="101 Coffee Lane",
                city="Nairobi",
                country="Kenya",
                latitude=-1.2834,
                longitude=36.8198,
                photos=[],
                rating=4.3,
                review_count=56
            )
        ]
        logger.info(f"Generated {len(mock_businesses)} mock businesses for testing")
        return mock_businesses
    
    async def recommend_based_on_preferences(
        self, 
        preferences: UserPreferences
    ) -> List[BusinessResponse]:
        """Recommend businesses based on user preferences with flexible matching"""
        try:
            all_businesses = await self.get_all_businesses()
            logger.info(f"Filtering {len(all_businesses)} businesses based on preferences: {preferences}")
            
            if not all_businesses:
                logger.warning("No businesses available for recommendations")
                return []
            
            # Simple filtering based on preferences
            filtered_businesses = []
            for business in all_businesses:
                # Check location (case-insensitive partial match)
                location_match = True
                if preferences.location and business.location:
                    location_match = preferences.location.lower() in business.location.lower()
                
                if not location_match:
                    continue
                
                # Check price range if specified
                price_match = True
                if preferences.price_range and business.price is not None:
                    business_price_range = self._get_price_range(business.price)
                    price_match = (business_price_range == preferences.price_range)
                
                if not price_match:
                    continue
                
                # Check interests - search in name, description, AND categories
                interest_match = False
                if preferences.interests:
                    # Prepare searchable text from business
                    searchable_text = f"{business.name.lower()} {business.description.lower()}"
                    if business.categories:
                        searchable_text += " " + " ".join([cat.lower() for cat in business.categories])
                    
                    # Check if any interest matches in the searchable text
                    for interest in preferences.interests:
                        if interest.lower() in searchable_text:
                            interest_match = True
                            break
                else:
                    # If no interests specified, match all businesses that passed location/price filters
                    interest_match = True
                
                if interest_match:
                    filtered_businesses.append(business)
            
            logger.info(f"Found {len(filtered_businesses)} businesses matching preferences")
            
            # If no matches found with strict filtering, try more relaxed matching
            if not filtered_businesses and preferences.interests:
                logger.info("Trying relaxed matching for interests...")
                for business in all_businesses:
                    # Only check location loosely
                    location_ok = True
                    if preferences.location and business.location:
                        location_ok = preferences.location.lower() in business.location.lower()
                    
                    if not location_ok:
                        continue
                    
                    # Try fuzzy matching on interests
                    searchable_text = f"{business.name.lower()} {business.description.lower()}"
                    if business.categories:
                        searchable_text += " " + " ".join([cat.lower() for cat in business.categories])
                    
                    for interest in preferences.interests:
                        # Try partial word matching
                        interest_words = interest.lower().split()
                        for word in interest_words:
                            if len(word) > 3 and word in searchable_text:
                                filtered_businesses.append(business)
                                break
            
            # Remove duplicates
            seen_ids = set()
            unique_businesses = []
            for business in filtered_businesses:
                if business.id not in seen_ids:
                    seen_ids.add(business.id)
                    unique_businesses.append(business)
            
            logger.info(f"Returning {len(unique_businesses)} unique businesses after filtering")
            
            # Sort by rating (no sponsored prioritization)
            unique_businesses.sort(key=lambda b: -(b.rating or 0))
            
            return unique_businesses
            
        except Exception as e:
            logger.error(f"Error in recommend_based_on_preferences: {e}")
            return []
    
    def _get_price_range(self, price: float) -> PriceRange:
        """Convert price value to price range category"""
        if price is None:
            return PriceRange.MODERATE  # Default if price is not available
        
        if price < 1000:
            return PriceRange.BUDGET
        elif price < 5000:
            return PriceRange.MODERATE
        else:
            return PriceRange.PREMIUM
    
    async def debug_business_categories(self):
        """Debug method to see what categories are available in the businesses"""
        all_businesses = await self.get_all_businesses()
        all_categories = set()
        
        for business in all_businesses:
            if business.categories:
                for category in business.categories:
                    all_categories.add(category)
        
        logger.info(f"Available categories in businesses: {sorted(all_categories)}")
        return sorted(all_categories)
    
    async def recommend_based_on_behavior(
        self, 
        user_id: Optional[int] = None
    ) -> List[BusinessResponse]:
        """Recommend businesses based on user behavior"""
        all_businesses = await self.get_all_businesses()
        
        # If no user ID provided, return popular businesses
        if not user_id:
            return await self.get_popular_businesses()
        
        # Get user's behavior from memory
        user_behavior = self.user_behavior.get(user_id, {})
        viewed_businesses = user_behavior.get("viewed", [])
        purchased_businesses = user_behavior.get("purchased", [])
        
        if not viewed_businesses and not purchased_businesses:
            # If no behavior data, return popular businesses
            return await self.get_popular_businesses()
        
        # Simple recommendation: businesses similar to those purchased
        recommendations = []
        for business_id in purchased_businesses:
            purchased_business = next(
                (b for b in all_businesses if b.id == business_id), 
                None
            )
            if purchased_business:
                # Find similar businesses (same category)
                similar = [
                    b for b in all_businesses 
                    if b.id != business_id and 
                    any(cat in purchased_business.categories for cat in b.categories)
                ]
                recommendations.extend(similar)
        
        # If no purchased items, use viewed items
        if not recommendations and viewed_businesses:
            for business_id in viewed_businesses:
                viewed_business = next(
                    (b for b in all_businesses if b.id == business_id), 
                    None
                )
                if viewed_business:
                    similar = [
                        b for b in all_businesses 
                        if b.id != business_id and 
                        any(cat in viewed_business.categories for cat in b.categories)
                    ]
                    recommendations.extend(similar)
        
        # Remove duplicates and return
        seen = set()
        unique_recommendations = []
        for business in recommendations:
            if business.id not in seen:
                seen.add(business.id)
                unique_recommendations.append(business)
        
        return unique_recommendations if unique_recommendations else await self.get_popular_businesses()
    
    async def track_user_behavior(
        self, 
        user_id: Optional[int], 
        business_id: str, 
        action: str
    ):
        """Track user behavior (clicks/purchases)"""
        if not user_id:
            return  # Skip tracking if no user ID
        
        # Get existing behavior data
        if user_id not in self.user_behavior:
            self.user_behavior[user_id] = {"viewed": [], "purchased": []}
        
        behavior_data = self.user_behavior[user_id]
        
        # Update based on action
        if action in ["click", "view"] and business_id not in behavior_data["viewed"]:
            behavior_data["viewed"].append(business_id)
            # Keep only recent 20 entries
            if len(behavior_data["viewed"]) > 20:
                behavior_data["viewed"].pop(0)
        
        if action == "purchase" and business_id not in behavior_data["purchased"]:
            behavior_data["purchased"].append(business_id)
            # Keep only recent 10 entries
            if len(behavior_data["purchased"]) > 10:
                behavior_data["purchased"].pop(0)
    
    async def get_popular_businesses(self) -> List[BusinessResponse]:
        """Get popular businesses sorted by rating and reviews"""
        all_businesses = await self.get_all_businesses()
        # Sort by rating and review count descending
        all_businesses.sort(key=lambda b: ((b.rating or 0), (b.review_count or 0)), reverse=True)
        return all_businesses[:10]


# Create a singleton instance
# recommendation_service = RecommendationService()
_recommendation_service = None

def set_recommendation_service(service: RecommendationService):
    global _recommendation_service
    _recommendation_service = service

def get_recommendation_service() -> RecommendationService:
    if _recommendation_service is None:
        raise RuntimeError("RecommendationService is not initialized")
    return _recommendation_service