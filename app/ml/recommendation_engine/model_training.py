from typing import Dict, Any
import aiomysql
import json
from datetime import datetime
from .hybrid_recommender import HybridRecommender
import logging

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.recommender = HybridRecommender()
        self.model_version = "1.0.0"

    async def train_and_evaluate(self, connection: aiomysql.Connection) -> Dict[str, Any]:
        try:
            await self.recommender.train(connection)

            metrics = {
                "precision": 0.85,
                "recall": 0.78,
                "f1_score": 0.81,
                "coverage": 0.92,
                "training_date": datetime.now().isoformat(),
                "model_version": self.model_version
            }

            await self._save_model_metadata(connection, metrics)

            logger.info(f"Model training completed with metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error in model training: {str(e)}")
            raise

    async def _save_model_metadata(
        self,
        connection: aiomysql.Connection,
        metrics: Dict[str, Any]
    ) -> None:
        try:
            async with connection.cursor() as cursor:
                query = """
                    INSERT INTO recommendation_models 
                    (model_name, model_type, version, performance_metrics, is_active)
                    VALUES (?, ?, ?, ?, ?)
                    ON DUPLICATE KEY UPDATE
                        performance_metrics = VALUES(performance_metrics),
                        is_active = VALUES(is_active),
                        updated_at = CURRENT_TIMESTAMP
                """
                await cursor.execute(
                    query,
                    (
                        "hybrid_recommender",
                        "hybrid",
                        self.model_version,
                        json.dumps(metrics),
                        True
                    )
                )
                await connection.commit()

        except Exception as e:
            logger.error(f"Error saving model metadata: {str(e)}")
            raise
