import numpy as np
import pandas as pd
import math
from typing import Dict, List
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

    def __init__(self, num_games=10):
        self.num_games = num_games

    def _normal_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

    def calculate_confidence(self, game_logs: pd.DataFrame, prop_line: float, stat_type: str) -> Dict:
        stat_col = self.STAT_COLS[stat_type]
        recent_stats = game_logs[stat_col].head(self.num_games).values

        if len(recent_stats) == 0:
            return self._empty_confidence()

        mu = np.mean(recent_stats)
        sigma = np.std(recent_stats)
        pick_direction = 'OVER' if mu > prop_line else 'UNDER'

        # Base probability from normal distribution
        # P(OVER) = 1 - Φ((line - μ) / σ)
        # P(UNDER) = Φ((line - μ) / σ)
        if sigma < 1e-6:
            base_prob = 1.0 if (
                (pick_direction == 'OVER' and mu > prop_line) or
                (pick_direction == 'UNDER' and mu < prop_line)
            ) else 0.0
        else:
            z = (prop_line - mu) / sigma
            base_prob = (1.0 - self._normal_cdf(z)) if pick_direction == 'OVER' else self._normal_cdf(z)

        trend_score = self._calculate_trend(recent_stats)
        consistency_score = self._calculate_consistency(recent_stats)

        trend_adj = (trend_score - 0.85) * 0.27
        consistency_adj = (consistency_score - 0.5) * 0.08

        confidence = float(np.clip(base_prob + trend_adj + consistency_adj, 0.0, 1.0))

        # Raw hit rate for display only, this is unsmoothed
        n = len(recent_stats)
        raw_hits = int(np.sum(recent_stats > prop_line) if pick_direction == 'OVER' else np.sum(recent_stats < prop_line))
        hit_rate = raw_hits / n if n > 0 else 0.0
        last_5_avg = np.mean(recent_stats[:5])

        return {
            'confidence': round(confidence * 100, 1),
            'hit_rate': round(hit_rate * 100, 1),
            'average': round(mu, 1),
            'last_5_avg': round(last_5_avg, 1),
            'std_dev': round(sigma, 2),
            'trend': self._get_trend_direction(recent_stats),
            'pick': pick_direction,
            'recent_games': recent_stats.tolist()[:10]
        }

    def _calculate_hit_rate(self, stats, line, pick_direction, alpha=2.0, beta=2.0):
        n = len(stats)
        if n == 0:
            return 0.5
        hits = np.sum(stats > line) if pick_direction == 'OVER' else np.sum(stats < line)
        return (hits + alpha) / (n + alpha + beta)

    def _calculate_trend(self, stats: np.ndarray) -> str:
        if len(stats) < 6:
            return 0.85
        last_5_avg = np.mean(stats[:5])
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

    def _get_trend_direction(self, stats: np.ndarray) -> str:
        if len(stats) < 6:
            return 'neutral'
        
        last_5_avg = np.mean(stats[:5])
        prev_5_avg = np.mean(stats[5:10])

        if last_5_avg > prev_5_avg * 1.05:
            return 'up'
        elif last_5_avg < prev_5_avg * 0.95:
            return 'down'
        else:
            return 'neutral'


    def _calculate_consistency(self, stats: np.ndarray) -> float:
        average = np.mean(stats)
        if average == 0:
            return 0
        std_dev = np.std(stats)
        cov = std_dev / average

        consistency = max(0, min(1, 1 - (cov - 0.2) / 0.3))
        return consistency

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
    
    def analyze_player(self, game_logs: pd.DataFrame, player_name: str, prop_lines: Dict[str, float]) -> List[Dict]:
        predicts = []
        for stat_type, prop_line in prop_lines.items():
            if stat_type not in self.STAT_COLS:
                continue
            confidence = self.calculate_confidence(game_logs, prop_line, stat_type)
            prediction = {
                'player_name': player_name,
                'stat_type': stat_type,
                'line': prop_line,
                **confidence
            }

            predicts.append(prediction)
        return predicts
    
    def rank_picks(self, predictions: List[Dict], min_confidence: float = 60.0, top_n: int = 5) -> List[Dict]:
        min_confidence_filtered = [p for p in predictions if p['confidence'] >= min_confidence]
        sorted_picks = sorted(min_confidence_filtered, key=lambda x: x['confidence'], reverse=True)
        return sorted_picks[:top_n]

    def generate_picks(self, pick: Dict) -> str:
        player = pick['player_name']
        stat = pick['stat_type']
        line = pick['line']
        prediction = pick['pick']
        confidence = pick['confidence']
        hit_rate = pick['hit_rate']
        average = pick['average']

        summary = (
            f"{player} {stat} {prediction} {line} "
            f"(Confidence: {confidence}%)\n"
            f" - Average: {average}\n"
            f" - {prediction} Hit Rate: {hit_rate}%\n"
            f"Trend: {pick['trend']}"
        )

        return summary

    
    
