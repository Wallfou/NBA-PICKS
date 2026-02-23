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
        'hit_rate': 0.65,
        'trend': 0.10,
        'consistency': 0.1,
        'cushion': 0.15
    }

    def __init__(self, num_games=10):
        self.num_games = num_games
    
    def calculate_confidence(self, game_logs: pd.DataFrame, prop_line: float, stat_type: str) -> Dict:
        stat_col = self.STAT_COLS[stat_type]
        recent_stats = game_logs[stat_col].head(self.num_games).values

        if (len(recent_stats) == 0):
            return self._empty_confidence()

        average = np.mean(recent_stats)
        pick_direction = 'OVER' if average > prop_line else 'UNDER'
        
        # Calculate hit rate based on pick direction
        hit_rate = self._calculate_hit_rate(recent_stats, prop_line, pick_direction)
        trend_score = self._calculate_trend(recent_stats)
        consistency_score = self._calculate_consistency(recent_stats)
        cushion_score = self._calculate_cushion(recent_stats, prop_line, pick_direction)

        confidence = (
            hit_rate * self.WEIGHTS['hit_rate'] +
            trend_score * self.WEIGHTS['trend'] +
            consistency_score * self.WEIGHTS['consistency'] +
            cushion_score * self.WEIGHTS['cushion']
        )

        std_dev = np.std(recent_stats)
        last_5_avg = np.mean(recent_stats[:5])

        return {
            'confidence': round(confidence * 100, 1),
            'hit_rate': round(hit_rate * 100, 1),
            'average': round(average, 1),
            'last_5_avg': round(last_5_avg, 1),
            'std_dev': round(std_dev, 2),
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

    def _calculate_cushion(self, stats, line, pick_direction):
        avg = np.mean(stats)
        if line <= 0:
            return 0.5

        signed = (avg - line) if pick_direction == 'OVER' else (line - avg)
        dist = signed / line

        if dist <= 0:
            return max(0.0, 0.5 + dist * 5)
        return min(1.0, 0.5 + dist * 5)

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

    
    
