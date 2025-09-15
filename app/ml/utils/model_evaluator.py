from typing import List, Dict, Any
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score
import logging

logger = logging.getLogger(__name__)

class ModelEvaluator:
    @staticmethod
    def evaluate_recommendations(true_positives: List[str], recommendations: List[str], k: int = 10) -> Dict[str, float]:
        """Evaluate recommendation quality using precision@k, recall@k, and F1@k"""
        if not true_positives or not recommendations:
            return {"precision": 0, "recall": 0, "f1": 0}
        
        # Get top-k recommendations
        top_k = recommendations[:k]
        
        # Calculate hits
        hits = [1 if item in true_positives else 0 for item in top_k]
        
        # Calculate metrics
        precision = sum(hits) / len(top_k) if top_k else 0
        recall = sum(hits) / len(true_positives) if true_positives else 0
        
        # Calculate F1 score
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0
        
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)
        }
    
    @staticmethod
    def calculate_coverage(all_items: List[str], recommended_items: List[str]) -> float:
        """Calculate catalog coverage of recommendations"""
        if not all_items:
            return 0
        
        unique_recommended = set(recommended_items)
        coverage = len(unique_recommended) / len(all_items)
        
        return round(coverage, 4)
    
    @staticmethod
    def calculate_novelty(recommendation_counts: Dict[str, int], recommendations: List[str]) -> float:
        """Calculate novelty of recommendations (average inverse popularity)"""
        if not recommendations:
            return 0
        
        total_items = sum(recommendation_counts.values())
        novelty_scores = []
        
        for item in recommendations:
            popularity = recommendation_counts.get(item, 0) / total_items if total_items > 0 else 0
            novelty = -np.log(popularity + 1e-10)  # Add small epsilon to avoid log(0)
            novelty_scores.append(novelty)
        
        avg_novelty = np.mean(novelty_scores) if novelty_scores else 0
        return round(avg_novelty, 4)