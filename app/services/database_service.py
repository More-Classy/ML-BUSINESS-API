import aiomysql
from typing import List, Dict, Optional
from app.models.schemas import BusinessResponse
import logging
import json
import random

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        # Removed self.sponsored_businesses

    async def get_all_businesses_from_db(self, limit: Optional[int] = None) -> List[BusinessResponse]:
        try:
            logger.info("Fetching businesses directly from MySQL database")

            base_query = """
            SELECT 
                b.businessID as id,
                b.name,
                b.description,
                b.address,
                b.city,
                b.country,
                b.latitude,
                b.longitude,
                b.isVerified,
                GROUP_CONCAT(DISTINCT s.subCategoryName) as categories,
                GROUP_CONCAT(DISTINCT p.photoURL) as photos,
                COALESCE(AVG(r.rating), 0) as rating,
                COUNT(r.reviewID) as review_count
            FROM Businesses b
            LEFT JOIN BusinessSubCategories bs ON b.businessID = bs.businessID
            LEFT JOIN SubCategories s ON bs.subCategoryID = s.subCategoryID
            LEFT JOIN BusinessPhotos p ON b.businessID = p.businessID
            LEFT JOIN Reviews r ON b.businessID = r.businessID
            GROUP BY b.businessID
            """

            # Enforce max limit cap
            max_limit = 100
            if limit is not  None:
                limit = min(limit, max_limit) if limit > 0 else max_limit
                query = base_query + f" ORDER BY RAND() LIMIT {limit}"
            else:
                query = base_query + " ORDER BY RAND()"

            # Add ORDER BY RAND() for randomization and limit for performance
            # query = base_query + f" ORDER BY RAND() LIMIT {limit}"

            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query)
                    results = await cursor.fetchall()

            businesses = []
            for row in results:
                business = self._parse_db_row(row)
                if business:
                    businesses.append(business)

            logger.info(f"Successfully loaded {len(businesses)} businesses from database")
            return businesses

        except Exception as e:
            logger.error(f"Error fetching businesses from database: {e}")
            return []

    def _parse_db_row(self, row: Dict) -> Optional[BusinessResponse]:
        """Parse database row to BusinessResponse"""
        try:
            categories_str = row.get('categories') or ''
            categories = [cat.strip() for cat in categories_str.split(',') if cat.strip()]

            photos_str = row.get('photos') or ''
            photos = [photo.strip() for photo in photos_str.split(',') if photo.strip()]

            mapped_data = {
                'id': row.get('id', ''),
                'name': row.get('name', '').strip(),
                'description': row.get('description', '').strip(),
                'address': row.get('address', ''),
                'city': row.get('city', ''),
                'country': row.get('country', ''),
                'latitude': row.get('latitude'),
                'longitude': row.get('longitude'),
                'location': f"{row.get('city', '')}, {row.get('country', '')}".strip(', '),
                'categories': categories,
                'price': random.uniform(500, 5000),  # Keep random price for now
                'photos': photos,
                'rating': float(row.get('rating', 0)),
                'review_count': int(row.get('review_count', 0))
            }

            return BusinessResponse(**mapped_data)

        except Exception as e:
            logger.warning(f"Failed to parse database row: {e}")
            return None


    async def fetch_user_preferences(self, user_id: int) -> Optional[Dict]:
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    query = """
                        SELECT user_id, interests, location, price_range, last_updated 
                        FROM user_preferences 
                        WHERE user_id = %s
                    """
                    await cur.execute(query, (user_id,))
                    return await cur.fetchone()
        except Exception as e:
            logger.error(f"Error fetching user preferences: {str(e)}")
            return None

    async def fetch_businesses_by_ids(self, business_ids: List[str]) -> List[Dict]:
        if not business_ids:
            return []
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    placeholders = ','.join(['%s'] * len(business_ids))
                    query = f"""
                        SELECT BusinessID, BusinessName, Description, Location, 
                               Latitude, Longitude, Rating, ReviewCount, PriceLevel
                        FROM Businesses 
                        WHERE BusinessID IN ({placeholders}) AND IsActive = TRUE
                    """
                    await cur.execute(query, business_ids)
                    return await cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching businesses by IDs: {str(e)}")
            return []

    async def execute_query(self, query: str, *params) -> List[Dict]:
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    return await cur.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return []

    async def save_user_preferences(self, user_id: int, interests: List[str],
                                    location: Optional[str], price_range: str) -> bool:
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    interests_json = json.dumps(interests)
                    query = """
                        INSERT INTO user_preferences 
                        (user_id, interests, location, price_range, last_updated)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            interests = VALUES(interests),
                            location = VALUES(location),
                            price_range = VALUES(price_range),
                            last_updated = NOW()
                    """
                    await cur.execute(query, (user_id, interests_json, location, price_range))
                    await conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
            return False

    async def log_user_behavior(self, user_id: int, business_id: str,
                                action_type: str, duration_seconds: int = 0,
                                metadata: Optional[Dict] = None) -> bool:
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    metadata_json = json.dumps(metadata) if metadata else None
                    query = """
                        INSERT INTO user_behavior 
                        (user_id, business_id, action_type, duration_seconds, metadata, action_timestamp)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """
                    await cur.execute(query, (user_id, business_id, action_type, duration_seconds, metadata_json))
                    await conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error logging user behavior: {str(e)}")
            return False


# Global instance
database_service = None

async def create_db_service(db_pool):
    global database_service
    database_service = DatabaseService(db_pool)
    return database_service

def get_db_service():
    return database_service
