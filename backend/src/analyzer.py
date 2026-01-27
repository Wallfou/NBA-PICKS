import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class NBAAnalyzer:
    STAT_COLS = {
        'PTS': 'PTS',
        'REB': 'REB',
        'AST': 'AST',
        'BLK': 'BLK',
        'STL': 'STL',
        'FG3M': 'FG3M',
        'MIN': 'MIN'
    }

    WEIGHTS = {
        'hit_rate': 0.45,
        'trend': 0.20,
        'consistency': 0.20,
        'cushion': 0.15
    }

    def __init__(self, num_games=10):
        self.num_games = num_games
    
    def calculate_confidence(self, game_logs: pd.DataFrame, prop_line: float, stat_type: str) -> Dict:
        stat_col = self.STAT_COLS[stat_type]
        recent_stats = game_logs[stat_col].head(self.num_games).values

        if (len(recent_stats) == 0):
            return self._empty_confidence()

        hit_rate = self._calculate_hit_rate(recent_stats, prop_line)
        trend_score = self._calculate_trend(recent_stats)
        consistency_score = self._calculate_consistency(recent_stats)
        cushion_score = self._calculate_cushion(recent_stats, prop_line)

        confidence = (
            hit_rate * self.WEIGHTS['hit_rate'] +
            trend_score * self.WEIGHTS['trend'] +
            consistency_score * self.WEIGHTS['consistency'] +
            cushion_score * self.WEIGHTS['cushion']
        )

        average = np.mean(recent_stats)
        std_dev = np.std(recent_stats)
        last_5_avg = np.mean(recent_stats[-5:])

        return {
            'confidence': round(confidence * 100, 1),
            'hit_rate': round(hit_rate * 100, 1),
            'average': round(average, 1),
            'last_5_avg': round(last_5_avg, 1),
            'std_dev': round(std_dev, 2),
            'trend': self._get_trend_direction(recent_stats),
            'pick': 'OVER' if average > prop_line else 'UNDER',
            'recent_games': recent_stats.tolist()[:10]
        }

    def _calculate_hit_rate(self, stats: np.ndarray, line: float) -> float:
        hits = np.sum(stats > line)
        return hits / len(stats) if len(stats) > 0 else 0

    def _calculate_trend(self, stats: np.ndarray) -> str:
        if len(stats) < 6:
            return 0.85
        last_5_avg = np.mean(stats[-5:])
        prev_5_avg = np.mean(stats[5:10])

        if prev_5_avg == 0:
            return 0.85
        trend = (last_5_avg - prev_5_avg) / prev_5_avg
        
        if trend >= 0.1:
            return 1.0
        elif trend >= 0:
            return 0.85 + (trend * 1.5)
        else: 
            return max(0.7, 0.85 + trend)
        



        
    def _empty_confidence(self) -> Dict:
        return {
            'confidence': 0,
            'hit_rate': 0,
            'average': 0,
            'last_5_avg': 0,
            'std_dev': 0,
            'trend': 'neutral',
            'pick': 'N/A',
            'recent_games': []
        }
    
