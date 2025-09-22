from typing import List
import aiomysql
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class ContentBasedRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.business_vectors = None
        self.business_ids = []

    async def train(self, connection: aiomysql.Connection):
        try:
            async with connection.cursor(aiomysql.DictCursor) as cur:
                query = """
                    SELECT b.BusinessID, b.BusinessName, b.Description, 
                           GROUP_CONCAT(DISTINCT c.CategoryName) AS categories,
                           GROUP_CONCAT(DISTINCT t.TagName) AS tags
                    FROM Businesses b
                    LEFT JOIN BusinessSubCategories bsc ON b.BusinessID = bsc.BusinessID
                    LEFT JOIN Categorys c ON bsc.CategoryID = c.CategoryID
                    LEFT JOIN BusinessTags bt ON b.BusinessID = bt.BusinessID
                    LEFT JOIN Tags t ON bt.TagID = t.TagID
                    WHERE b.IsActive = TRUE
                    GROUP BY b.BusinessID
                """
                await cur.execute(query)
                businesses = await cur.fetchall()

            if not businesses:
                logger.warning("No businesses found for training")
                return

            text_data = []
            self.business_ids = []

            for b in businesses:
                combined_text = f"{b['BusinessName']} {b.get('Description', '')} {b.get('categories', '')} {b.get('tags', '')}"
                text_data.append(combined_text)
                self.business_ids.append(b['BusinessID'])

            self.business_vectors = self.vectorizer.fit_transform(text_data)
            logger.info(f"Content-based recommender trained on {len(self.business_ids)} businesses")

        except Exception as e:
            logger.error(f"Error training content-based recommender: {str(e)}")
            raise

    async def get_recommendations(self, user_interests: List[str], limit: int = 10) -> List[str]:
        if self.business_vectors is None or not self.business_ids:
            return []

        try:
            query_text = " ".join(user_interests)
            query_vector = self.vectorizer.transform([query_text])
            similarities = cosine_similarity(query_vector, self.business_vectors).flatten()
            top_indices = np.argsort(similarities)[::-1][:limit]
            return [self.business_ids[i] for i in top_indices if similarities[i] > 0]

        except Exception as e:
            logger.error(f"Error generating content-based recommendations: {str(e)}")
            return []
