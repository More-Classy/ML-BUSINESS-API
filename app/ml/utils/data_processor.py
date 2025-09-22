import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    @staticmethod
    def preprocess_user_behavior_data(behavior_data: List[Dict]) -> pd.DataFrame:
        """Preprocess user behavior data for ML models"""
        if not behavior_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(behavior_data)
        
        # Convert action types to numerical weights
        action_weights = {
            'click': 1,
            'share': 2,
            'purchase': 3
        }
        
        df['weight'] = df['action_type'].map(action_weights)
        
        # Add time-based decay (more recent interactions have higher weight)
        if 'action_timestamp' in df.columns:
            df['action_timestamp'] = pd.to_datetime(df['action_timestamp'])
            most_recent = df['action_timestamp'].max()
            df['recency_weight'] = 1 / (1 + (most_recent - df['action_timestamp']).dt.days / 30)  # 30-day half-life
            df['weight'] = df['weight'] * df['recency_weight']
        
        return df
    
    @staticmethod
    def create_user_item_matrix(behavior_df: pd.DataFrame, user_col: str = 'user_id', 
                              item_col: str = 'business_id') -> pd.DataFrame:
        """Create user-item interaction matrix"""
        if behavior_df.empty:
            return pd.DataFrame()
        
        # Create pivot table with user-item interactions
        interaction_matrix = behavior_df.pivot_table(
            index=user_col,
            columns=item_col,
            values='weight',
            aggfunc='sum',
            fill_value=0
        )
        
        return interaction_matrix
    
    @staticmethod
    def normalize_scores(scores: np.ndarray) -> np.ndarray:
        """Normalize scores to 0-1 range"""
        if len(scores) == 0:
            return scores
        
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        if max_score == min_score:
            return np.ones_like(scores)
        
        return (scores - min_score) / (max_score - min_score)