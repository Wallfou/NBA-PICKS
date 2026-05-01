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

    # helper: convert american odds (-250) to payout multiplier (1.4)
    def _american_to_payout(self, price):
        if price is None:
            return None
        if price >= 100:
            return price / 100.0
        if price <= -100:
            return 100.0 / abs(price)
        return None

    def calculate_confidence(self, game_logs: pd.DataFrame, prop_line: float, stat_type: str) -> Dict:
        stat_col = self.STAT_COLS[stat_type]
        recent_stats = game_logs[stat_col].head(self.num_games).values

        if len(recent_stats) == 0:
            return self._empty_confidence()

        mu = np.mean(recent_stats)
        sigma = np.std(recent_stats)

        if sigma < 1e-6:
            if mu > prop_line:
                p_over = 1.0
            elif mu < prop_line:
                p_over = 0.0
            else:
                p_over = 0.5
        else:
            z = (prop_line - mu) / sigma
            p_over = 1.0 - self._normal_cdf(z)

        pick_direction = 'OVER' if p_over >= 0.5 else 'UNDER'
        base_prob = p_over if pick_direction == 'OVER' else 1.0 - p_over

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
    
    
    def analyze_player(self, game_logs: pd.DataFrame, player_name: str, prop_lines: Dict[str, Dict]) -> List[Dict]:
        predicts = []
        for stat_type, prop in prop_lines.items():
            if stat_type not in self.STAT_COLS:
                continue
            line = prop['line']
            over_price = prop.get('over_price')
            under_price = prop.get('under_price')

            confidence = self.calculate_confidence(game_logs, line, stat_type)

            pick = confidence['pick']
            price = over_price if pick == 'OVER' else under_price
            payout = self._american_to_payout(price)
            p = confidence['confidence'] / 100.0
            ev = round(p * payout - (1 - p), 4) if payout is not None else None

            prediction = {
                'player_name': player_name,
                'stat_type': stat_type,
                'line': line,
                'over_price': over_price,
                'under_price': under_price,
                'price': price,
                'payout': round(payout, 4) if payout is not None else None,
                'ev': ev,
                **confidence
            }

            predicts.append(prediction)
        return predicts

    def rank_picks(self, predictions: List[Dict], min_ev: float = 0.0, min_confidence: float = 0.0, top_n: int = 5) -> List[Dict]:
        eligible = [
            p for p in predictions
            if p.get('ev') is not None
            and p['ev'] >= min_ev
            and p.get('confidence', 0) >= min_confidence
        ]
        sorted_picks = sorted(eligible, key=lambda x: x['ev'], reverse=True)
        return sorted_picks[:top_n]

    def generate_picks(self, pick: Dict) -> str:
        player = pick['player_name']
        stat = pick['stat_type']
        line = pick['line']
        prediction = pick['pick']
        confidence = pick['confidence']
        hit_rate = pick['hit_rate']
        average = pick['average']
        price = pick.get('price')
        ev = pick.get('ev')

        price_str = f"{price:+d}" if price is not None else "N/A"
        ev_str = f"{ev:+.3f}" if ev is not None else "N/A"

        summary = (
            f"{player} {stat} {prediction} {line} @ {price_str} "
            f"(EV: {ev_str}, Confidence: {confidence}%)\n"
            f" - Average: {average}\n"
            f" - {prediction} Hit Rate: {hit_rate}%\n"
            f"Trend: {pick['trend']}"
        )

        return summary

    
    
