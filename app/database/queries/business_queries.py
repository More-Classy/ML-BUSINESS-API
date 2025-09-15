from typing import List, Optional
import aiomysql

class BusinessQueries:
    @staticmethod
    async def get_businesses_by_category(
        conn: aiomysql.Connection, 
        category_ids: List[int], 
        limit: int = 10,
        offset: int = 0
    ) -> List[dict]:
        """Get businesses by category IDs"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Convert list to comma-separated placeholders
            placeholders = ','.join(['%s'] * len(category_ids))
            query = f"""
                SELECT b.*, c.categoryName 
                FROM Businesses b 
                JOIN BusinessSubCategories bsc ON b.businessID = bsc.businessID
                JOIN Categorys c ON bsc.categoryID = c.categoryID
                WHERE c.categoryID IN ({placeholders})
                ORDER BY b.rating DESC, b.reviewCount DESC
                LIMIT %s OFFSET %s
            """
            await cur.execute(query, category_ids + [limit, offset])
            return await cur.fetchall()

    @staticmethod
    async def get_business_by_id(
        conn: aiomysql.Connection, 
        business_id: int
    ) -> Optional[dict]:
        """Get business by ID"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT b.*, 
                       GROUP_CONCAT(DISTINCT c.categoryName) AS categories,
                       GROUP_CONCAT(DISTINCT t.tagName) AS tags
                FROM Businesses b
                LEFT JOIN BusinessSubCategories bsc ON b.businessID = bsc.businessID
                LEFT JOIN Categorys c ON bsc.categoryID = c.categoryID
                LEFT JOIN BusinessTags bt ON b.businessID = bt.businessID
                LEFT JOIN Tags t ON bt.tagID = t.tagID
                WHERE b.businessID = %s
                GROUP BY b.businessID
            """
            await cur.execute(query, (business_id,))
            result = await cur.fetchone()
            return result

    @staticmethod
    async def search_businesses(
        conn: aiomysql.Connection,
        query_text: str,
        location: Optional[str] = None,
        category_id: Optional[int] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[dict]:
        """Search businesses with filters"""
        async with conn.cursor(aiomysql.DictCursor) as cur:
            base_query = """
                SELECT b.*, c.categoryName,
                       MATCH(b.businessName, b.description) AGAINST (%s IN NATURAL LANGUAGE MODE) AS relevance
                FROM Businesses b
                LEFT JOIN BusinessSubCategories bsc ON b.businessID = bsc.businessID
                LEFT JOIN Categorys c ON bsc.categoryID = c.categoryID
                WHERE MATCH(b.businessName, b.description) AGAINST (%s IN NATURAL LANGUAGE MODE)
            """
            params = [query_text, query_text]
            conditions = []

            if location:
                conditions.append("b.location LIKE %s")
                params.append(f"%{location}%")

            if category_id:
                conditions.append("c.categoryID = %s")
                params.append(category_id)

            if conditions:
                base_query += " AND " + " AND ".join(conditions)

            base_query += " ORDER BY relevance DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            await cur.execute(base_query, params)
            return await cur.fetchall()
