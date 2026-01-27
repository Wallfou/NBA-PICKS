from nba_api.stats.endpoints import scoreboardv2, playergamelog
from datetime import datetime
import pandas as pd

class NBAFetcher:
    def __init__(self):
        pass

    def get_today_games(self):
        today = datetime.now().strftime('%Y-%m-%d')
        board = scoreboardv2.ScoreboardV2(game_date=today)

        return board.game_header.get_data_frame()

    def get_player_stats(self, player_id, num_games=15):
        log = playergamelog.PlayerGameLog(
            player_id=player_id,
            season='2025-26',
            season_type_all_star='Regular Season'
        )
        
        df = log.get_data_frames()[0]
        
        return df.head(num_games)