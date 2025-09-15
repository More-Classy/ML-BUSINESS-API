from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.services.onboarding_service import AIOnboardingService, ServiceCategory

# Create the router first
router = APIRouter()

# Pydantic Models
class BusinessDescriptionRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100, description="Name of the business")
    services: List[str] = Field(..., max_items=4, min_items=1, description="Business services as free text (max 4)")
    location: Optional[str] = Field(None, max_length=100, description="Business location (optional)")
    
    @validator('services')
    def validate_services_count(cls, v):
        if len(v) > 4:
            raise ValueError('Maximum 4 services allowed')
        # Validate each service string
        for service in v:
            if not service.strip():
                raise ValueError('Service cannot be empty')
            if len(service) > 100:
                raise ValueError('Each service must be less than 100 characters')
        return v

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

class ProductSuggestionsRequest(BaseModel):
    services: List[str] = Field(..., max_items=4, min_items=1, description="Business services as free text (max 4)")

class ServiceSuggestionRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100, description="Name of the business")
    industry_hint: Optional[str] = Field(None, description="Optional industry hint")

class ServiceSuggestionResponse(BaseModel):
    suggested_services: List[str] = Field(..., description="AI-suggested services")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")

class BusinessDescriptionResponse(BaseModel):
    description: str = Field(..., description="AI-generated business description (100-200 words)")
    auto_filled_category: Optional[Dict] = Field(None, description="Automatically determined primary category")
    word_count: int = Field(..., description="Word count of description")
    success: bool = True

class BusinessCategoriesResponse(BaseModel):
    suggested_categories: List[Dict] = Field(..., description="AI-matched categories from backend")
    suggested_subcategories: List[Dict] = Field(..., description="Relevant subcategories")
    suggested_tags: List[Dict] = Field(..., max_items=10, description="AI-suggested tags (max 10)")
    confidence_score: float = Field(..., ge=0, le=1, description="AI confidence in suggestions")
    success: bool = True

class BusinessImagesResponse(BaseModel):
    image_url: str = Field(..., description="Single targeted business image URL")
    image_description: str = Field(..., description="Description of the image")
    search_query_used: str = Field(..., description="Actual search query used for transparency")
    success: bool = True

class ProductSuggestionsResponse(BaseModel):
    products: List[Dict[str, str]] = Field(..., max_items=3, description="Max 3 AI-generated products")
    success: bool = True

class ErrorResponse(BaseModel):
    error: str
    success: bool = False
@router.post(
    "/suggest-services",
    response_model=ServiceSuggestionResponse,
    summary="Suggest services",
    description="Suggest services for a business based on name and industry hint",
    tags=["AI Onboarding"]
)
async def suggest_services(
    request: ServiceSuggestionRequest,
    onboarding_service: AIOnboardingService = Depends()
):
    """
    Suggest services for a business based on name and optional industry hint
    
    Flow: Business name → AI suggests relevant services → Returns 4-8 service suggestions
    """
    try:
        result = await onboarding_service.suggest_services(
            request.business_name, 
            request.industry_hint
        )
        
        return ServiceSuggestionResponse(
            suggested_services=result["services"],
            confidence=result["confidence"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suggest services: {str(e)}"
        )
@router.post(
    "/suggest-categories",
    response_model=BusinessCategoriesResponse,
    summary="Suggest business categories",
    description="AI-powered category suggestions from free text services",
    tags=["AI Onboarding"]
)
async def suggest_categories(
    request: BusinessCategoriesRequest,
    onboarding_service: AIOnboardingService = Depends()
):
    """
    Step 2: AI-powered category suggestions
    
    Flow: Services only (max 4) → Backend categories called → AI suggests best matches with confidence
    """
    try:
        # Fetch backend categories
        backend_categories = await onboarding_service.get_backend_categories()
        
        if not backend_categories:
            return BusinessCategoriesResponse(
                suggested_categories=[],
                suggested_subcategories=[],
                suggested_tags=[],
                confidence_score=0.0
            )
        
        # AI category matching
        ai_result = await onboarding_service.ai_suggest_categories(request.services, backend_categories)
        matched_categories = ai_result["matched_categories"]
        
        # Get subcategories and tags for matched categories
        suggested_subcategories = []
        suggested_tags = []
        
        for category in matched_categories:
            # Extract subcategories
            subcats = category.get('subCategories', [])
            suggested_subcategories.extend(subcats[:3])  # Limit per category
            
            # Get tags for this category
            category_tags = await onboarding_service.get_backend_tags(category.get('categoryID'))
            suggested_tags.extend(category_tags[:5])  # Limit per category
        
        return BusinessCategoriesResponse(
            suggested_categories=matched_categories,
            suggested_subcategories=suggested_subcategories[:8],  # Overall limit
            suggested_tags=suggested_tags[:10],  # Overall limit
            confidence_score=ai_result["confidence"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suggest categories: {str(e)}"
        )

@router.post(
    "/generate-description",
    response_model=BusinessDescriptionResponse,
    summary="Generate business description",
    description="Generate AI business description with auto-filled category",
    tags=["AI Onboarding"]
)
async def generate_description(
    request: BusinessDescriptionRequest,
    onboarding_service: AIOnboardingService = Depends()
):
    """
    Step 1: Generate AI business description with auto-filled category
    
    Flow: Business name + Services (max 4) + Optional location → Auto-filled category → AI description (100-200 words)
    """
    try:
        # Auto-determine primary category
        auto_category = await onboarding_service.auto_determine_category(
            request.business_name, 
            request.services
        )
        
        # Generate regulated description
        description_result = await onboarding_service.generate_business_description(
            request.business_name,
            request.services,
            request.location
        )
        
        return {
            "description": description_result["description"],
            "auto_filled_category": auto_category,
            "word_count": description_result["word_count"],
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )



@router.post(
    "/generate-images",
    response_model=BusinessImagesResponse,
    summary="Generate business image",
    description="Generate a single, highly targeted business image from services",
    tags=["AI Onboarding"]
)
async def generate_images(
    request: BusinessImagesRequest,
    onboarding_service: AIOnboardingService = Depends()
):
    """
    Step 3: Generate single business image from services only
    
    Flow: Services only (max 4) → Extract key keywords → Generate precise search query → Return single targeted image
    
    Improvements:
    - Single, highly targeted image instead of 2 generic ones
    - Direct keyword extraction from services
    - Precise search queries (e.g., "coffee" for coffee services)
    - Better accuracy and relevance
    """
    try:
        result = await onboarding_service.generate_business_images(request.services)
        
        # Extract the single image data
        image_url = result["image_urls"][0] if result["image_urls"] else ""
        image_description = result["descriptions"][0] if result["descriptions"] else ""
        
        # Get the search query that was used for transparency
        search_query = onboarding_service._create_precise_search_query(request.services)
        
        return BusinessImagesResponse(
            image_url=image_url,
            image_description=image_description,
            search_query_used=search_query,
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {str(e)}"
        )

@router.post(
    "/suggest-products",
    response_model=ProductSuggestionsResponse,
    summary="Suggest products",
    description="Generate product suggestions based on services",
    tags=["AI Onboarding"]
)
async def suggest_products(
    request: ProductSuggestionsRequest,
    onboarding_service: AIOnboardingService = Depends()
):
    """
    Step 4: Generate product suggestions based on services
    
    Flow: Services (max 4) → Generate 3 products relevant to the services
    """
    try:
        # Generate products based on services
        products = await onboarding_service.generate_product_suggestions(request.services)
        
        return ProductSuggestionsResponse(products=products, success=True)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suggest products: {str(e)}"
        )



@router.get(
    "/services",
    summary="Get service categories",
    description="Get all available service categories for frontend dropdown",
    tags=["AI Onboarding"]
)
async def get_available_services():
    """Get all available service categories for frontend dropdown"""
    return [
        {"value": service.value, "label": service.value.replace('_', ' ').title(), "description": f"{service.value.replace('_', ' ').title()} related services"}
        for service in ServiceCategory
    ]

@router.get(
    "/onboarding-flow",
    summary="Get onboarding flow",
    description="Get the complete onboarding flow structure for frontend",
    tags=["AI Onboarding"]
)
async def get_onboarding_flow():
    """Get the complete onboarding flow structure for frontend"""
    return {
        "steps": [
            {
                "step": 1,
                "name": "Business Description",
                "endpoint": "/api/v1/onboarding/generate-description",
                "description": "Generate AI business description with auto-category detection",
                "required_fields": ["business_name", "services"],
                "optional_fields": ["location"],
                "ai_features": ["Auto category detection", "Regulated description length (100-200 words)"]
            },
            {
                "step": 2,
                "name": "Category Suggestions",
                "endpoint": "/api/v1/onboarding/suggest-categories", 
                "description": "AI-powered category matching from backend",
                "required_fields": ["services"],
                "ai_features": ["Backend integration", "Confidence scoring", "Smart matching"]
            },
            {
                "step": 3,
                "name": "Business Image",
                "endpoint": "/api/v1/onboarding/generate-images",
                "description": "Generate single, highly targeted business image",
                "required_fields": ["services"],
                "ai_features": [
                    "Precise keyword extraction from services", 
                    "Direct search queries (e.g., 'coffee' for coffee services)",
                    "Single, highly relevant image",
                    "Search query transparency"
                ]
            },
            {
                "step": 4,
                "name": "Product Suggestions",
                "endpoint": "/api/v1/onboarding/suggest-products",
                "description": "Generate products with precise images based on services",
                "required_fields": ["services"],
                "ai_features": [
                    "Service-specific product generation", 
                    "3 products with keyword-focused images",
                    "Product name + service keyword image searches"
                ]
            }
        ],
        "image_generation_improvements": {
            "keyword_extraction": "Removes generic words like 'service', 'professional', focuses on core terms",
            "precise_queries": "Converts 'coffee services' → 'coffee', 'house cleaning services' → 'house cleaning'",
            "single_image": "One highly targeted image instead of 2 generic ones",
            "product_images": "Combines product name + service keywords for better relevance",
            "transparency": "Returns actual search query used for debugging/improvement"
        },
        "examples": {
            "input": ["coffee services", "espresso drinks"],
            "keyword_extraction": ["coffee", "espresso"],
            "search_query": "coffee espresso",
            "expected_result": "Image showing coffee/espresso related content"
        }
    }

@router.get(
    "/demo/complete-flow",
    summary="Demo complete flow",
    description="Demo endpoint showing complete AI onboarding flow",
    tags=["AI Onboarding"]
)
async def demo_complete_flow():
    """Demo endpoint showing complete AI onboarding flow"""
    return {
        "demo_business": {
            "name": "Bella Vista Restaurant",
            "services": ["Italian cuisine", "catering"],
            "location": "Downtown Nairobi"
        },
        "flow_demonstration": {
            "step_1": {
                "input": "Business name + services + location",
                "ai_processing": "Auto-detect category + Generate description",
                "output": "Professional description (100-200 words) + Auto-filled category"
            },
            "step_2": {
                "input": "Services only",
                "ai_processing": "Match with backend categories using AI",
                "output": "Suggested categories + subcategories + tags with confidence"
            },
            "step_3": {
                "input": "Services only", 
                "ai_processing": "Select service-specific stock images",
                "output": "2 professional business images"
            },
            "step_4": {
                "input": "Services",
                "ai_processing": "Generate service-specific products",
                "output": "3 products with service-specific images"
            }
        },
        "ai_enhancements": [
            "Regulated description length (100-200 words)",
            "Auto category detection throughout",
            "Service-based image selection",
            "Smart product generation based on services",
            "Confidence scoring for suggestions",
            "Backend integration with AI matching"
        ]
    }