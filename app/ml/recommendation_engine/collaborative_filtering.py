from typing import List
import aiomysql
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class CollaborativeFiltering:
    def __init__(self):
        self.user_similarity_matrix = None
        self.user_ids = []
        self.business_ids = []
        self.interaction_matrix = None

    async def train(self, connection: aiomysql.Connection):
        try:
            async with connection.cursor(aiomysql.DictCursor) as cur:
                query = """
                    SELECT ub.user_id, ub.business_id, 
                        CASE 
                            WHEN ub.action_type = 'purchase' THEN 3
                            WHEN ub.action_type = 'share' THEN 2 
                            WHEN ub.action_type = 'click' THEN 1
                            ELSE 0
                        END as weight
                    FROM user_behavior ub
                    JOIN Businesses b ON ub.business_id = b.BusinessID
                    WHERE b.IsActive = TRUE
                    AND ub.action_timestamp > NOW() - INTERVAL 90 DAY
                """
                await cur.execute(query)
                interactions = await cur.fetchall()

            if not interactions:
                logger.warning("No user interactions found for collaborative filtering")
                return

            user_ids = sorted(set(r['user_id'] for r in interactions))
            business_ids = sorted(set(r['business_id'] for r in interactions))

            interaction_matrix = np.zeros((len(user_ids), len(business_ids)))
            user_id_to_index = {uid: i for i, uid in enumerate(user_ids)}
            business_id_to_index = {bid: i for i, bid in enumerate(business_ids)}

            for r in interactions:
                ui = user_id_to_index[r['user_id']]
                bi = business_id_to_index[r['business_id']]
                interaction_matrix[ui, bi] = r['weight']

            self.user_similarity_matrix = cosine_similarity(interaction_matrix)
            self.user_ids = user_ids
            self.business_ids = business_ids
            self.interaction_matrix = interaction_matrix

            logger.info(f"Collaborative filtering trained on {len(user_ids)} users and {len(business_ids)} businesses")

        except Exception as e:
            logger.error(f"Error training collaborative filtering: {str(e)}")
            raise

    async def get_recommendations(self, user_id: int, limit: int = 10) -> List[str]:
        if self.user_similarity_matrix is None or user_id not in self.user_ids:
            return []

        try:
            user_idx = self.user_ids.index(user_id)
            user_similarities = self.user_similarity_matrix[user_idx]
            similar_user_indices = np.argsort(user_similarities)[::-1][1:6]

            similar_users_interactions = self.interaction_matrix[similar_user_indices]
            business_scores = np.sum(similar_users_interactions, axis=0)

            user_interactions = self.interaction_matrix[user_idx]
            interacted_indices = np.where(user_interactions > 0)[0]
            business_scores[interacted_indices] = 0

            top_indices = np.argsort(business_scores)[::-1][:limit]
            return [self.business_ids[i] for i in top_indices if business_scores[i] > 0]

        except Exception as e:
            logger.error(f"Error generating collaborative recommendations: {str(e)}")
            return []
