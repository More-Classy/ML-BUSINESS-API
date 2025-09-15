from typing import List, Optional
import aiomysql
from .content_based import ContentBasedRecommender
from .collaborative_filtering import CollaborativeFiltering
import logging

logger = logging.getLogger(__name__)

class HybridRecommender:
    def __init__(self):
        self.content_based = ContentBasedRecommender()
        self.collaborative = CollaborativeFiltering()
        self.is_trained = False

    async def train(self, connection: aiomysql.Connection):
        try:
            await self.content_based.train(connection)
            await self.collaborative.train(connection)
            self.is_trained = True
            logger.info("Hybrid recommender training completed")
        except Exception as e:
            logger.error(f"Error training hybrid recommender: {str(e)}")
            self.is_trained = False

    async def get_recommendations(
        self,
        user_id: int,
        user_interests: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[str]:
        if not self.is_trained:
            return []

        try:
            content_recs = await self.content_based.get_recommendations(
                user_interests or [], limit * 2
            ) if user_interests else []

            collab_recs = await self.collaborative.get_recommendations(
                user_id, limit * 2
            )

            all_recs = list(set(content_recs + collab_recs))

            if content_recs and collab_recs:
                content_count = min(limit // 2, len(content_recs))
                collab_count = min(limit // 2, len(collab_recs))
                final_recs = content_recs[:content_count] + collab_recs[:collab_count]
                remaining = limit - len(final_recs)
                if remaining > 0:
                    additional = [r for r in all_recs if r not in final_recs][:remaining]
                    final_recs.extend(additional)
                return final_recs[:limit]
            else:
                return all_recs[:limit]

        except Exception as e:
            logger.error(f"Error generating hybrid recommendations: {str(e)}")
            return []
