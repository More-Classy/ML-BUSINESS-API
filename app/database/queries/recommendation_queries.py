from typing import List, Dict
import aiomysql

class RecommendationQueries:
    @staticmethod
    async def get_popular_businesses(conn: aiomysql.Connection, limit: int = 10) -> List[Dict]:
        """Get popular businesses based on ratings and reviews"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT BusinessID, BusinessName, Description, Location, 
                       Latitude, Longitude, Rating, ReviewCount, PriceLevel
                FROM Businesses 
                WHERE IsActive = TRUE
                ORDER BY Rating DESC, ReviewCount DESC 
                LIMIT %s
            """
            await cur.execute(query, (limit,))
            return await cur.fetchall()

    @staticmethod
    async def get_businesses_by_category(conn: aiomysql.Connection, category_id: int, limit: int = 10) -> List[Dict]:
        """Get businesses by category ID"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT b.BusinessID, b.BusinessName, b.Description, b.Location, 
                       b.Latitude, b.Longitude, b.Rating, b.ReviewCount, b.PriceLevel
                FROM Businesses b
                JOIN BusinessSubCategories bsc ON b.BusinessID = bsc.BusinessID
                WHERE bsc.CategoryID = %s AND b.IsActive = TRUE
                ORDER BY b.Rating DESC, b.ReviewCount DESC
                LIMIT %s
            """
            await cur.execute(query, (category_id, limit))
            return await cur.fetchall()

    @staticmethod
    async def get_businesses_by_price_range(conn: aiomysql.Connection, price_level: int, limit: int = 10) -> List[Dict]:
        """Get businesses by price range"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT BusinessID, BusinessName, Description, Location, 
                       Latitude, Longitude, Rating, ReviewCount, PriceLevel
                FROM Businesses 
                WHERE PriceLevel = %s AND IsActive = TRUE
                ORDER BY Rating DESC, ReviewCount DESC
                LIMIT %s
            """
            await cur.execute(query, (price_level, limit))
            return await cur.fetchall()

    @staticmethod
    async def get_businesses_by_location(conn: aiomysql.Connection, location: str, limit: int = 10) -> List[Dict]:
        """Get businesses by location"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT BusinessID, BusinessName, Description, Location, 
                       Latitude, Longitude, Rating, ReviewCount, PriceLevel
                FROM Businesses 
                WHERE Location LIKE %s AND IsActive = TRUE
                ORDER BY Rating DESC, ReviewCount DESC
                LIMIT %s
            """
            await cur.execute(query, (f"%{location}%", limit))
            return await cur.fetchall()

    @staticmethod
    async def get_recently_added_businesses(conn: aiomysql.Connection, limit: int = 10) -> List[Dict]:
        """Get recently added businesses"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT BusinessID, BusinessName, Description, Location, 
                       Latitude, Longitude, Rating, ReviewCount, PriceLevel
                FROM Businesses 
                WHERE IsActive = TRUE
                ORDER BY CreatedAt DESC
                LIMIT %s
            """
            await cur.execute(query, (limit,))
            return await cur.fetchall()
