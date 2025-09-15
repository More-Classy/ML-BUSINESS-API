from typing import List, Optional, Dict
import aiomysql
from app.models.database_models import ActionType, PriceRange

class UserQueries:
    @staticmethod
    async def track_user_behavior(
        conn: aiomysql.Connection,
        user_id: int,
        business_id: str,
        action_type: ActionType,
        duration_seconds: int = 0,
        metadata: Optional[Dict] = None
    ) -> int:
        """Track user behavior (click, share, or purchase)"""
        async with conn.cursor() as cur:
            query = """
                INSERT INTO user_behavior 
                (user_id, business_id, action_type, duration_seconds, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """
            await cur.execute(query, (user_id, business_id, action_type.value, duration_seconds, str(metadata)))
            await conn.commit()
            return cur.lastrowid

    @staticmethod
    async def get_user_behavior(
        conn: aiomysql.Connection,
        user_id: int,
        limit: int = 100,
        action_type: Optional[ActionType] = None
    ) -> List[Dict]:
        """Get user behavior history"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = "SELECT * FROM user_behavior WHERE user_id = %s"
            params = [user_id]

            if action_type:
                query += " AND action_type = %s"
                params.append(action_type.value)

            query += " ORDER BY action_timestamp DESC LIMIT %s"
            params.append(limit)

            await cur.execute(query, tuple(params))
            return await cur.fetchall()

    @staticmethod
    async def get_user_preferences(
        conn: aiomysql.Connection,
        user_id: int
    ) -> Optional[Dict]:
        """Get user preferences"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = "SELECT * FROM user_preferences WHERE user_id = %s"
            await cur.execute(query, (user_id,))
            return await cur.fetchone()

    @staticmethod
    async def create_user_preferences(
        conn: aiomysql.Connection,
        user_id: int,
        interests: List[str],
        location: Optional[str] = None,
        price_range: PriceRange = PriceRange.MODERATE
    ) -> int:
        """Create or update user preferences"""
        async with conn.cursor() as cur:
            query = """
                INSERT INTO user_preferences 
                (user_id, interests, location, price_range)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    interests = VALUES(interests),
                    location = VALUES(location),
                    price_range = VALUES(price_range),
                    last_updated = CURRENT_TIMESTAMP
            """
            await cur.execute(query, (user_id, str(interests), location, price_range.value))
            await conn.commit()
            return cur.lastrowid

    @staticmethod
    async def update_user_preferences(
        conn: aiomysql.Connection,
        user_id: int,
        interests: Optional[List[str]] = None,
        location: Optional[str] = None,
        price_range: Optional[PriceRange] = None
    ) -> bool:
        """Update user preferences"""
        async with conn.cursor() as cur:
            updates = []
            params = []

            if interests is not None:
                updates.append("interests = %s")
                params.append(str(interests))

            if location is not None:
                updates.append("location = %s")
                params.append(location)

            if price_range is not None:
                updates.append("price_range = %s")
                params.append(price_range.value)

            if not updates:
                return False

            query = f"""
                UPDATE user_preferences 
                SET {', '.join(updates)}, last_updated = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            params.append(user_id)
            await cur.execute(query, tuple(params))
            await conn.commit()
            return cur.rowcount > 0

    @staticmethod
    async def get_users_with_similar_interests(
        conn: aiomysql.Connection,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Find users with similar interests (basic LIKE-based filtering)"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Fallback implementation: compare common string interests (not JSON_TABLE)
            query = """
                SELECT up.user_id, up.interests
                FROM user_preferences up
                WHERE up.user_id != %s
                  AND EXISTS (
                      SELECT 1 FROM user_preferences tp 
                      WHERE tp.user_id = %s 
                      AND up.interests LIKE CONCAT('%', tp.interests, '%')
                  )
                LIMIT %s
            """
            await cur.execute(query, (user_id, user_id, limit))
            return await cur.fetchall()

    @staticmethod
    async def get_user_behavior_stats(
        conn: aiomysql.Connection,
        user_id: int
    ) -> Dict[str, Dict[str, float]]:
        """Get statistics about user behavior"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT 
                    action_type,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration
                FROM user_behavior 
                WHERE user_id = %s
                GROUP BY action_type
            """
            await cur.execute(query, (user_id,))
            rows = await cur.fetchall()

            stats = {}
            for row in rows:
                stats[row['action_type']] = {
                    'count': row['count'],
                    'avg_duration': float(row['avg_duration']) if row['avg_duration'] else 0
                }

            return stats
