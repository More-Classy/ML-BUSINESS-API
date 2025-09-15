from app.core.config import settings

def __init__(self):
    self.csharp_backend_url = settings.CSHARP_BACKEND_URL
    self.business_endpoint = settings.CSHARP_BUSINESS_ENDPOINT
    self.cache = {}  # Simple in-memory cache
    self.user_behavior = {}  # Store user behavior in memory
    self.sponsored_businesses = {}  # Track which businesses are sponsored