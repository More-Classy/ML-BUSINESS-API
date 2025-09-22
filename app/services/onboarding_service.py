from fastapi import HTTPException
from openai import OpenAI
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import json
import httpx
import os
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
import urllib.parse
import aiohttp
from app.core.config import settings

logger = logging.getLogger(__name__)

class ServiceCategory(str, Enum):
    RESTAURANTS = "RESTAURANTS"
    AUTO = "AUTO"
    BRANDS = "BRANDS" 
    HEALTH = "HEALTH"
    MALLS = "MALLS"
    STORES = "STORES"
    SERVICES = "SERVICES"
    BEAUTY_SPA = "BEAUTY_SPA"
    PROPERTIES = "PROPERTIES"

class AIOnboardingService:
    def __init__(self):
        try:
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                logger.warning("OpenAI API key not set, AI features will be limited")
                self.client = None
            else:
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI client initialized successfully")
            
            self.backend_base_url = settings.CSHARP_BACKEND_URL
            
            # Pexels API configuration
            self.pexels_api_key = settings.PEXELS_API_KEY
            if self.pexels_api_key:
                logger.info("Pexels API key found")
            else:
                logger.warning("Pexels API key not set, using fallback images")
            
            logger.info(f"Backend URL: {self.backend_base_url}")
            
            # Enhanced service mappings for auto-category detection
            self.service_keywords_mapping = {
                "restaurant": ServiceCategory.RESTAURANTS,
                "food": ServiceCategory.RESTAURANTS,
                "dining": ServiceCategory.RESTAURANTS,
                "cafe": ServiceCategory.RESTAURANTS,
                "cuisine": ServiceCategory.RESTAURANTS,
                "catering": ServiceCategory.RESTAURANTS,
                "auto": ServiceCategory.AUTO,
                "car": ServiceCategory.AUTO,
                "vehicle": ServiceCategory.AUTO,
                "mechanic": ServiceCategory.AUTO,
                "repair": ServiceCategory.AUTO,
                "automotive": ServiceCategory.AUTO,
                "transport": ServiceCategory.AUTO,
                "logistics": ServiceCategory.AUTO,
                "brand": ServiceCategory.BRANDS,
                "manufacturer": ServiceCategory.BRANDS,
                "luxury": ServiceCategory.BRANDS,
                "consumer": ServiceCategory.BRANDS,
                "health": ServiceCategory.HEALTH,
                "medical": ServiceCategory.HEALTH,
                "clinic": ServiceCategory.HEALTH,
                "hospital": ServiceCategory.HEALTH,
                "wellness": ServiceCategory.HEALTH,
                "pharmacy": ServiceCategory.HEALTH,
                "doctor": ServiceCategory.HEALTH,
                "dental": ServiceCategory.HEALTH,
                "x-ray": ServiceCategory.HEALTH,
                "ent": ServiceCategory.HEALTH,
                "mall": ServiceCategory.MALLS,
                "shopping": ServiceCategory.MALLS,
                "retail": ServiceCategory.STORES,
                "store": ServiceCategory.STORES,
                "shop": ServiceCategory.STORES,
                "merchandise": ServiceCategory.STORES,
                "consulting": ServiceCategory.SERVICES,
                "professional": ServiceCategory.SERVICES,
                "business": ServiceCategory.SERVICES,
                "finance": ServiceCategory.SERVICES,
                "legal": ServiceCategory.SERVICES,
                "education": ServiceCategory.SERVICES,
                "training": ServiceCategory.SERVICES,
                "communication": ServiceCategory.SERVICES,
                "beauty": ServiceCategory.BEAUTY_SPA,
                "spa": ServiceCategory.BEAUTY_SPA,
                "salon": ServiceCategory.BEAUTY_SPA,
                "massage": ServiceCategory.BEAUTY_SPA,
                "skincare": ServiceCategory.BEAUTY_SPA,
                "property": ServiceCategory.PROPERTIES,
                "real estate": ServiceCategory.PROPERTIES,
                "housing": ServiceCategory.PROPERTIES,
                "rental": ServiceCategory.PROPERTIES,
                "land": ServiceCategory.PROPERTIES
            }
            
            # Service suggestion cache
            self.service_cache = {}
            self.cache_timeout = timedelta(hours=24)
            
            # Common services database fallback
            self.common_services_by_industry = {
                "restaurant": [
                    "Fine Dining", "Casual Dining", "Takeaway", "Catering",
                    "Private Events", "Wine Selection", "Desserts", "Coffee Bar"
                ],
                "auto": [
                    "Car Repair", "Oil Change", "Tire Service", "Brake Service",
                    "Engine Diagnostics", "Car Wash", "Auto Detailing", "AC Service"
                ],
                "health": [
                    "General Consultation", "Specialist Referral", "Health Checkup",
                    "Vaccination", "Pharmacy", "Lab Tests", "X-Ray Services", "Dental Care"
                ],
                "retail": [
                    "Product Sales", "Customer Service", "Delivery", "Gift Wrapping",
                    "Product Consultation", "Warranty Services", "Installation", "Repairs"
                ],
                "beauty": [
                    "Hair Styling", "Manicure/Pedicure", "Facial Treatments", "Massage",
                    "Waxing", "Makeup Services", "Spa Treatments", "Skin Care"
                ],
                "technology": [
                    "IT Support", "Software Development", "Web Design", "Network Setup",
                    "Data Recovery", "Cyber Security", "Cloud Services", "Tech Consulting"
                ],
                "education": [
                    "Tutoring", "Test Preparation", "Skill Development", "Online Courses",
                    "Certification Programs", "Workshops", "Career Counseling", "Language Classes"
                ],
                "construction": [
                    "General Contracting", "Renovation", "Electrical Work", "Plumbing",
                    "Painting", "Carpentry", "Rooftop", "Landscaping"
                ]
            }

            # Direct service-to-image mapping for precise results
            self.direct_image_mapping = {
                # Oil services
                "engine oil": "car engine oil bottle motor oil change",
                "oil change": "mechanic pouring engine oil car maintenance",
                "motor oil": "motor oil bottles lubricant automotive fluid",
                "oil service": "professional oil change service garage",
                
                # Hair services
                "haircut": "hair stylist cutting client hair salon",
                "hairdressing": "hairdresser styling woman hair salon professional",
                "hair styling": "hair stylist working blow dry salon",
                "hair salon": "modern hair salon interior stylists working",
                
                # Auto parts
                "gearbox": "car gearbox transmission parts automotive",
                "engine": "car engine motor automotive parts",
                "brake": "car brake pads disc brake system",
                "tire": "car tires wheel automotive rubber",
                "spark plugs": "spark plugs engine parts automotive ignition",
                "transmission": "car transmission gearbox automotive repair",
                
                # Beauty services
                "manicure": "nail manicure hands nail polish salon",
                "pedicure": "pedicure feet nail care spa treatment",
                "facial": "facial treatment skincare spa massage",
                "massage": "massage therapy spa relaxation treatment",
                "spa": "luxury spa treatment room wellness center",
                
                # Medical services
                "x-ray": "medical x-ray equipment radiography hospital",
                "dental": "dental clinic dentist examining patient",
                "clinic": "medical clinic doctor patient examination",
                "pharmacy": "pharmacy medicines pills medical supplies",
                
                # Food services
                "restaurant": "elegant restaurant interior dining tables",
                "catering": "catering buffet food presentation event",
                "coffee": "barista making coffee espresso machine cafe",
                "bakery": "bakery fresh bread pastries display",
                
                # Repair services
                "electronics repair": "electronics repair technician circuit board",
                "phone repair": "mobile phone repair technician tools",
                "computer repair": "computer technician repairing laptop",
                
                # Construction
                "plumbing": "plumber installing pipes bathroom renovation",
                "electrical": "electrician installing wiring electrical panel",
                "painting": "house painter painting wall roller brush",
                "carpentry": "carpenter working wood tools workshop",
                
                # Professional services
                "accounting": "accountant working calculator financial documents",
                "legal": "lawyer office law books professional consultation",
                "consulting": "business consultation meeting professionals"
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self.client = None

    async def suggest_services_from_public_api(self, business_name: str, industry_hint: Optional[str] = None):
        """Fetch service suggestions from public APIs"""
        try:
            # Try Google Places API (requires API key)
            google_places_key = os.getenv("GOOGLE_PLACES_API_KEY")
            if google_places_key and industry_hint:
                async with aiohttp.ClientSession() as session:
                    # Search for similar businesses
                    search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json"
                    params = {
                        "query": f"{industry_hint} {business_name}",
                        "key": google_places_key,
                        "language": "en"
                    }
                    
                    async with session.get(search_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('results'):
                                # Extract services from business types
                                services = set()
                                for result in data['results']:
                                    if 'types' in result:
                                        services.update(
                                            t.replace('_', ' ').title() 
                                            for t in result['types'] 
                                            if not t.startswith('point_of_interest')
                                        )
                                return list(services)[:8]
            
            # Fallback to common services based on industry hint
            if industry_hint:
                industry_lower = industry_hint.lower()
                for industry, services in self.common_services_by_industry.items():
                    if industry in industry_lower:
                        return services[:6]
            
            # Ultimate fallback - general services
            return [
                "Consultation", "Customer Support", "Delivery", 
                "Installation", "Maintenance", "Repair", "Training"
            ]
            
        except Exception as e:
            logger.error(f"Public API service suggestion failed: {str(e)}")
            return None

    async def ai_suggest_services(self, business_name: str, industry_hint: Optional[str] = None):
        """AI-powered service suggestions"""
        if not self.client:
            return await self.suggest_services_from_public_api(business_name, industry_hint)
        
        try:
            # Check cache first
            cache_key = f"{business_name.lower()}_{industry_hint.lower() if industry_hint else 'general'}"
            cached = self.service_cache.get(cache_key)
            if cached and datetime.now() < cached['expiry']:
                return cached['services']
            
            prompt = f"""
            Business Name: "{business_name}"
            {f"Industry Hint: {industry_hint}" if industry_hint else ""}
            
            Suggest 6-8 specific services this business might offer. 
            Make them realistic, professional, and specific to the business type.
            
            Requirements:
            - 6-8 services total
            - Each service: 2-4 words maximum
            - Be specific and actionable (not generic)
            - Relevant to the business name and industry
            - Different types of services (not all the same)
            
            Return as a JSON array of strings:
            {{
                "services": ["Service 1", "Service 2", "Service 3", ...],
                "confidence": 0.95
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            services = result.get("services", [])
            
            # Cache the results
            self.service_cache[cache_key] = {
                'services': services,
                'expiry': datetime.now() + self.cache_timeout
            }
            
            return services
            
        except Exception as e:
            logger.error(f"AI service suggestion failed: {str(e)}")
            return await self.suggest_services_from_public_api(business_name, industry_hint)

    async def suggest_services(self, business_name: str, industry_hint: Optional[str] = None) -> Dict:
        """Main service suggestion method with confidence scoring"""
        try:
            # Try AI suggestion first
            ai_services = await self.ai_suggest_services(business_name, industry_hint)
            
            if ai_services and len(ai_services) >= 4:
                return {
                    "services": ai_services[:8],  # Max 8 suggestions
                    "confidence": 0.85,
                    "source": "ai_generated"
                }
            
            # Fallback to public API/common services
            fallback_services = await self.suggest_services_from_public_api(business_name, industry_hint)
            
            return {
                "services": fallback_services[:6] if fallback_services else [
                    "General Consultation", "Customer Service", 
                    "Professional Services", "Quality Support"
                ],
                "confidence": 0.7,
                "source": "common_services"
            }
            
        except Exception as e:
            logger.error(f"Service suggestion failed: {str(e)}")
            return {
                "services": [
                    "Consultation Services", "Customer Support",
                    "Professional Assistance", "Quality Service"
                ],
                "confidence": 0.6,
                "source": "fallback"
            }

    async def auto_determine_category(self, business_name: str, services: List[str]) -> Optional[Dict]:
        """AI-powered auto category detection from free text services"""
        if not self.client:
            # Fallback keyword matching
            return self._fallback_category_detection(services)
        
        try:
            services_text = ', '.join(services)
            
            prompt = f"""
            Business: "{business_name}"
            Services offered: [{services_text}]
            
            Analyze and determine the PRIMARY business category:
            
            Categories:
            - RESTAURANTS: Food service, dining, cafes, catering
            - AUTO: Vehicle services, repairs, sales, transport, logistics
            - HEALTH: Medical, wellness, healthcare, clinics, pharmacies
            - STORES: Retail, shopping, merchandise, goods
            - SERVICES: Professional services, consulting, business solutions
            - BEAUTY_SPA: Beauty treatments, spa services, wellness
            - PROPERTIES: Real estate, property management, housing
            - BRANDS: Brand manufacturing, consumer goods, luxury items
            - MALLS: Shopping centers, retail complexes
            
            Return JSON: {{"category": "EXACT_CATEGORY_NAME", "confidence": 0.95, "reasoning": "brief explanation"}}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Auto-determined category: {result.get('category')} with confidence {result.get('confidence')}")
            
            return {
                "name": result.get("category"),
                "confidence": result.get("confidence", 0.8),
                "reasoning": result.get("reasoning", "AI analysis")
            }
            
        except Exception as e:
            logger.error(f"Auto category detection failed: {str(e)}")
            return self._fallback_category_detection(services)

    def _fallback_category_detection(self, services: List[str]) -> Optional[Dict]:
        """Fallback category detection using keyword matching"""
        service_text_lower = ' '.join(services).lower()
        
        for keyword, category in self.service_keywords_mapping.items():
            if keyword in service_text_lower:
                return {
                    "name": category.value,
                    "confidence": 0.7,
                    "reasoning": f"Keyword match: {keyword}"
                }
        
        return {
            "name": ServiceCategory.SERVICES.value,
            "confidence": 0.5,
            "reasoning": "Default fallback"
        }
    

    def _clean_description_formatting(self, description: str) -> str:
        """Clean and properly format the description text"""
        # Remove any escaped characters
        description = description.replace('\\n', '<br><br>')
        description = description.replace('\\n', '\n')
        description = description.replace('\\\\', '\\')
        
        # Split into sentences and rejoin properly
        sentences = [s.strip() for s in description.split('.') if s.strip()]
        
        # Group sentences into paragraphs (roughly 2-3 sentences per paragraph)
        paragraphs = []
        current_paragraph = []
        
        for i, sentence in enumerate(sentences):
            current_paragraph.append(sentence)
            
            # Create paragraph break every 2-3 sentences
            if len(current_paragraph) >= 2 and (i == len(sentences) - 1 or len(current_paragraph) == 3):
                paragraphs.append('. '.join(current_paragraph) + '.')
                current_paragraph = []
        
        # Add any remaining sentences
        if current_paragraph:
            paragraphs.append('. '.join(current_paragraph) + '.')
        
        # Join paragraphs with actual line breaks (not escaped)
        cleaned_description = '\n\n'.join(paragraphs)
        
        return cleaned_description

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_business_description(self, business_name: str, services: List[str], location: Optional[str] = None) -> Dict:
        """Generate regulated-length AI business description from free text services"""
        if not self.client:
            # Fallback description
            services_text = ', '.join(services)
            location_text = f" located in {location}" if location else ""
            description = f"{business_name} specializes in {services_text}{location_text}. We are committed to delivering exceptional service and value to our customers.\n\nOur experienced team ensures quality and customer satisfaction in all our offerings. Contact us today to experience the difference quality service makes."
            return {"description": description, "word_count": len(description.split())}
        
        try:
            services_text = ', '.join(services)
            location_clause = f" in {location}" if location else ""
            
            prompt = f"""
            Write a professional business description for "{business_name}" that offers: {services_text}{location_clause}.
            
            Requirements:
            - EXACTLY 100-200 words (strict limit)
            - Professional, engaging tone
            - Focus on customer value and unique selling points
            - Include what makes this business special
            - Be specific about the services mentioned: {services_text}
            - End with a call to action
            - Make it sound established and credible
            - Write in clear paragraphs separated by blank lines
            - Structure: Introduction paragraph, then services paragraph, then closing/CTA paragraph
            
            Write as if this business already exists and is successful.
            Return only the description text without any additional formatting or markup.
            """
            
            logger.info(f"Generating description for {business_name} with services: {services_text}")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            
            raw_description = response.choices[0].message.content.strip()
            
            # Clean and format the description properly
            description = self._clean_description_formatting(raw_description)
            word_count = len(description.split())
            
            logger.info(f"Generated description with {word_count} words")
            return {"description": description, "word_count": word_count}
            
        except Exception as e:
            logger.error(f"Description generation failed: {str(e)}")
            # Enhanced fallback with proper formatting
            services_text = ', '.join(services)
            location_text = f" in {location}" if location else ""
            description = f"{business_name} excels in providing {services_text}{location_text}. We combine expertise with innovation to deliver outstanding results for our clients.\n\nOur commitment to excellence and customer satisfaction sets us apart in the industry. Experience the difference with our professional services designed to meet your specific needs and exceed expectations."
            return {"description": description, "word_count": len(description.split())}

    def _extract_exact_service_keyword(self, services: List[str]) -> str:
        """Extract the most specific service keyword for precise image matching"""
        if not services:
            return "business"
        
        # Convert all services to lowercase for matching
        all_services_text = ' '.join(services).lower()
        
        # Check for exact matches in our direct mapping first (prioritize multi-word matches)
        # Sort by length to prioritize longer/more specific matches first
        sorted_keywords = sorted(self.direct_image_mapping.keys(), key=len, reverse=True)
        for keyword in sorted_keywords:
            if keyword in all_services_text:
                logger.info(f"Found exact match for keyword: '{keyword}'")
                return keyword
        
        # If no exact match, find the most specific service phrase
        stop_words = {'services', 'service', 'professional', 'quality', 'premium', 
                     'business', 'company', 'and', 'the', 'for', 'with', 'of', 'production',
                     'manufacturing', 'installation', 'repair', 'maintenance', 'cleaning'}
        
        # Prioritize multi-word services over single words
        specific_phrases = []
        for service in services:
            # Remove common generic words from the service name
            words = service.lower().split()
            filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
            
            if filtered_words:
                # Create phrases of different lengths (prioritize longer phrases)
                if len(filtered_words) >= 2:
                    # Try 2-word phrases first
                    specific_phrases.append(' '.join(filtered_words[:2]))
                # Then single words
                specific_phrases.extend(filtered_words)
        
        if specific_phrases:
            # Return the longest phrase available (most specific)
            return max(specific_phrases, key=len)
        
        # Fallback to the first service without stop words
        for service in services:
            words = service.lower().split()
            filtered_words = [word for word in words if word not in stop_words]
            if filtered_words:
                return ' '.join(filtered_words)
        
        return services[0].lower()

    def _get_direct_search_query(self, keyword: str) -> str:
        """Get direct search query from mapping or create precise one"""
        # Check direct mapping first
        if keyword in self.direct_image_mapping:
            return self.direct_image_mapping[keyword]
        
        # Create precise query for unmapped keywords
        precise_queries = {
            "welding": "welder welding metal sparks workshop",
            "roofing": "roofer installing roof tiles construction",
            "flooring": "flooring installation hardwood tiles worker",
            "cleaning": "professional cleaning service office commercial",
            "landscaping": "landscaper gardening lawn mower outdoor",
            "photography": "photographer camera professional studio",
            "catering": "catering chef preparing food event service",
            "tutoring": "tutor teaching student books education",
            "fitness": "personal trainer gym fitness equipment",
            "insurance": "insurance agent meeting client office",
            "accounting": "accountant calculator financial documents office",
            "web design": "web designer computer coding website development",
            "marketing": "marketing team meeting strategy presentation"
        }
        
        if keyword in precise_queries:
            return precise_queries[keyword]
        
        # Last resort: use the keyword as is
        return keyword

    def _create_precise_search_query(self, services: List[str]) -> str:
        """Create precise search query for transparency in API response"""
        exact_keyword = self._extract_exact_service_keyword(services)
        return self._get_direct_search_query(exact_keyword)

    async def fetch_pexels_images(self, query: str, count: int = 1) -> List[Dict[str, str]]:
        """Fetch images with exact query matching"""
        try:
            if not self.pexels_api_key:
                logger.warning("Pexels API key not available")
                return []
            
            # Add random page parameter for different results
            page = random.randint(1, 5)  # Random page between 1-5 for variety
            encoded_query = urllib.parse.quote(query)
            
            async with httpx.AsyncClient() as client:
                url = f"https://api.pexels.com/v1/search?query={encoded_query}&per_page={count}&orientation=landscape&page={page}"
                headers = {"Authorization": self.pexels_api_key}
                
                logger.info(f"Pexels search query: '{query}' (page {page})")
                
                response = await client.get(url, headers=headers, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    photos = data.get('photos', [])
                    
                    if photos:
                        result = []
                        for photo in photos[:count]:
                            image_url = (photo['src'].get('large2x') or 
                                       photo['src'].get('large') or 
                                       photo['src'].get('medium'))
                            
                            result.append({
                                "url": image_url,
                                "description": photo.get('alt', query),
                                "photographer": photo.get('photographer', 'Pexels')
                            })
                        
                        logger.info(f"Found {len(result)} images for query: '{query}'")
                        return result
                    else:
                        logger.warning(f"No images found for query: '{query}'")
                else:
                    logger.error(f"Pexels API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Pexels API request failed: {str(e)}")
        
        return []

    async def generate_business_images(self, services: List[str]) -> Dict[str, List[str]]:
        """Generate precise business images based on exact service keywords"""
        try:
            # Extract the most specific service keyword (now handles multi-word)
            exact_keyword = self._extract_exact_service_keyword(services)
            
            # Get the precise search query
            search_query = self._get_direct_search_query(exact_keyword)
            
            logger.info(f"Service: '{exact_keyword}' -> Search query: '{search_query}'")
            
            # Try primary search
            pexels_images = await self.fetch_pexels_images(search_query, 1)
            if pexels_images:
                return {
                    "image_urls": [pexels_images[0]["url"]],
                    "descriptions": [f"Professional {exact_keyword} service"]
                }
            
            # Fallback 1: Try just the exact keyword
            if exact_keyword != search_query:
                logger.info(f"Trying fallback search with exact keyword: '{exact_keyword}'")
                pexels_images = await self.fetch_pexels_images(exact_keyword, 1)
                if pexels_images:
                    return {
                        "image_urls": [pexels_images[0]["url"]],
                        "descriptions": [f"Professional {exact_keyword} service"]
                    }
            
            # Fallback 2: If multi-word, try individual words
            if ' ' in exact_keyword:
                words = exact_keyword.split()
                for word in words:
                    if len(word) > 3:  # Only try meaningful words
                        logger.info(f"Trying individual word: '{word}'")
                        pexels_images = await self.fetch_pexels_images(word, 1)
                        if pexels_images:
                            return {
                                "image_urls": [pexels_images[0]["url"]],
                                "descriptions": [f"Professional {exact_keyword} service"]
                            }
            
            # Fallback 3: Service-specific default images
            fallback_url = self._get_service_specific_fallback(exact_keyword)
            
            return {
                "image_urls": [fallback_url],
                "descriptions": [f"Professional {exact_keyword} service"]
            }
            
        except Exception as e:
            logger.error(f"Business image generation failed: {str(e)}")
            return {
                "image_urls": ["https://picsum.photos/800/600?random=123"],
                "descriptions": ["Professional business service"]
            }
    def _get_service_specific_fallback(self, keyword: str) -> str:
        """Get service-specific fallback image URL"""
        # Service-specific fallback images
        service_fallbacks = {
            "engine oil": "https://images.pexels.com/photos/13065690/pexels-photo-13065690.jpeg",
            "haircut": "https://images.pexels.com/photos/3993449/pexels-photo-3993449.jpeg",
            "manicure": "https://images.pexels.com/photos/3997379/pexels-photo-3997379.jpeg",
            "massage": "https://images.pexels.com/photos/3757942/pexels-photo-3757942.jpeg",
            "restaurant": "https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg",
            "coffee": "https://images.pexels.com/photos/302899/pexels-photo-302899.jpeg",
            "dental": "https://images.pexels.com/photos/6812549/pexels-photo-6812549.jpeg",
            "x-ray": "https://images.pexels.com/photos/7089020/pexels-photo-7089020.jpeg"
        }
        
        if keyword in service_fallbacks:
            return service_fallbacks[keyword]
        
        # Generate consistent fallback based on keyword hash
        keyword_hash = abs(hash(keyword)) % 1000
        return f"https://picsum.photos/800/600?random={keyword_hash}"
        
    async def get_backend_categories(self) -> List[Dict]:
        """Fetch categories from C# backend"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_base_url}/api/category", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.warning(f"Backend categories failed: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Backend categories fetch failed: {str(e)}")
            return []

    async def get_backend_tags(self, category_id: Optional[int] = None) -> List[Dict]:
        """Fetch tags from C# backend"""
        try:
            async with httpx.AsyncClient() as client:
                if category_id:
                    response = await client.post(
                        f"{self.backend_base_url}/api/Tag/GetByCategory",
                        json={"categoryId": category_id}
                    )
                else:
                    response = await client.get(f"{self.backend_base_url}/api/Tag")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return []
        except Exception as e:
            logger.error(f"Backend tags fetch failed: {str(e)}")
            return []

    async def ai_suggest_categories(self, services: List[str], backend_categories: List[Dict]) -> Dict:
        """AI-powered category suggestions from free text services - returns only the MOST relevant category"""
        if not self.client or not backend_categories:
            return {"matched_categories": [], "confidence": 0.5}
        
        try:
            services_text = ', '.join(services)
            
            # Prepare categories for AI analysis
            categories_info = []
            for cat in backend_categories[:10]:  # Limit for token efficiency
                subcats = [sub.get('subCategoryName', '') for sub in cat.get('subCategories', [])[:3]]
                categories_info.append({
                    "name": cat.get('categoryName', 'Unknown'),
                    "id": cat.get('categoryID'),
                    "subcategories": subcats
                })
            
            categories_text = "\n".join([
                f"- {cat['name']} (ID: {cat['id']}): {', '.join(cat['subcategories'])}"
                for cat in categories_info
            ])
            
            prompt = f"""
            Services offered: {services_text}
            
            Available Backend Categories:
            {categories_text}
            
            Analyze the services and select ONLY THE SINGLE MOST RELEVANT category with the highest confidence score.
            Consider how well the services match the category and its subcategories.
            
            Return JSON format:
            {{
                "selected_category": {{
                    "category_name": "exact_name", 
                    "category_id": id, 
                    "confidence": 0.95, 
                    "match_reason": "detailed explanation of why this is the best match"
                }},
                "overall_confidence": 0.95
            }}
            
            Be very selective - only return the single best match with high confidence.
            """
            
            logger.info(f"AI category matching for services: {services_text}")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            selected_category = ai_result.get("selected_category", {})
            
            # Match with actual backend category
            matched_categories = []
            if selected_category:
                for cat in backend_categories:
                    if cat.get('categoryName') == selected_category.get('category_name'):
                        enhanced_cat = cat.copy()
                        enhanced_cat['ai_confidence'] = selected_category.get('confidence', 0.8)
                        enhanced_cat['match_reason'] = selected_category.get('match_reason', 'AI match')
                        matched_categories.append(enhanced_cat)
                        break
            
            return {
                "matched_categories": matched_categories,  # contains only 1 category or empty
                "confidence": ai_result.get("overall_confidence", 0.8)
            }
            
        except Exception as e:
            logger.error(f"AI category suggestion failed: {str(e)}")
            return {"matched_categories": [], "confidence": 0.5}

    async def generate_product_images(self, services: List[str], product_name: str) -> str:
        """Generate precise product image using exact service keywords"""
        try:
            # Extract key terms from product name and services
            product_keywords = [word.lower() for word in product_name.split() 
                            if len(word) > 2 and word.lower() not in {'the', 'and', 'for', 'with'}]
            
            # Get exact service keyword (now handles multi-word services)
            service_keyword = self._extract_exact_service_keyword(services)
            
            # Create precise search query combining product and service
            if product_keywords:
                # Use the full service keyword, not just the first word
                search_query = f"{' '.join(product_keywords[:2])} {service_keyword}"
            else:
                search_query = service_keyword
            
            logger.info(f"Product image search: '{search_query}'")
            
            # Try Pexels with precise query (random page for variety)
            pexels_images = await self.fetch_pexels_images(search_query, 1)
            if pexels_images:
                return pexels_images[0]["url"]
            
            # If no results, try with just the service keyword
            if product_keywords and search_query != service_keyword:
                logger.info(f"Trying fallback search with service keyword only: '{service_keyword}'")
                pexels_images = await self.fetch_pexels_images(service_keyword, 1)
                if pexels_images:
                    return pexels_images[0]["url"]
            
            # Fallback with service-specific image
            return self._get_service_specific_fallback(service_keyword)
            
        except Exception as e:
            logger.error(f"Product image generation failed: {str(e)}")
            return self._get_service_specific_fallback("business")


    async def generate_product_suggestions(self, services: List[str]) -> List[Dict[str, str]]:
        """Generate exactly 3 product suggestions with precise images"""
        if not self.client:
            # Fallback products with precise images
            return [
                {
                    "name": "Premium Service",
                    "description": "High-quality service offering",
                    "image_url": await self.generate_product_images(services, "premium service")
                },
                {
                    "name": "Standard Package",
                    "description": "Popular choice for most customers",
                    "image_url": await self.generate_product_images(services, "standard package")
                },
                {
                    "name": "Basic Option",
                    "description": "Essential service at great value",
                    "image_url": await self.generate_product_images(services, "basic option")
                }
            ]
        
        try:
            services_text = ', '.join(services)
            
            prompt = f"""
            Generate EXACTLY 3 specific, realistic products/services for a business offering: {services_text}.
            
            Requirements:
            - Each product name: 2-4 words maximum, must be directly related to the services
            - Each description: 8-12 words maximum, describing the specific offering
            - Products should be concrete, specific offerings, not generic terms
            - Different price tiers or service levels (premium, standard, basic)
            - Must be directly relevant and specific to: {services_text}
            
            Examples for "Car Repair":
            - "Complete Oil Change Service" not "Oil Change"
            - "Premium Brake Replacement" not "Brake Service"
            - "Tire Rotation & Balancing" not "Tire Service"
            
            Return JSON:
            {{
                "products": [
                    {{"name": "Specific Product Name", "description": "Specific description under 12 words"}},
                    {{"name": "Specific Product Name", "description": "Specific description under 12 words"}},
                    {{"name": "Specific Product Name", "description": "Specific description under 12 words"}}
                ]
            }}
            """
            
            logger.info(f"Generating product suggestions for services: {services_text}")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            products = ai_result.get("products", [])[:3]  # Ensure exactly 3
            
            # Generate precise images for each product
            for product in products:
                product["image_url"] = await self.generate_product_images(services, product["name"])
            
            # Ensure we always have exactly 3 products
            while len(products) < 3:
                # Create more specific fallback products based on services
                service_keyword = self._extract_exact_service_keyword(services)
                fallback_names = [
                    f"Premium {service_keyword.title()} Package",
                    f"Standard {service_keyword.title()} Service",
                    f"Essential {service_keyword.title()} Option"
                ]
                
                for i, name in enumerate(fallback_names[len(products):3]):
                    products.append({
                        "name": name,
                        "description": f"Comprehensive {service_keyword} solution for your needs",
                        "image_url": await self.generate_product_images(services, name)
                    })
            
            return products[:3]  # Return exactly 3
            
        except Exception as e:
            logger.error(f"Product generation failed: {str(e)}")
            # Enhanced fallback with service-specific products
            service_keyword = self._extract_exact_service_keyword(services)
            fallback_products = [
                {
                    "name": f"Premium {service_keyword.title()} Package",
                    "description": f"Top-tier {service_keyword} with full features and support",
                    "image_url": await self.generate_product_images(services, f"premium {service_keyword}")
                },
                {
                    "name": f"Standard {service_keyword.title()} Service",
                    "description": f"Professional {service_keyword} solution for most needs",
                    "image_url": await self.generate_product_images(services, f"standard {service_keyword}")
                },
                {
                    "name": f"Essential {service_keyword.title()} Option",
                    "description": f"Basic {service_keyword} service at competitive pricing",
                    "image_url": await self.generate_product_images(services, f"basic {service_keyword}")
                }
            ]
            
            return fallback_products