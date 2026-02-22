from nba_api.stats.endpoints import scoreboardv2, playergamelog
from datetime import datetime, timedelta
import pandas as pd

class NBAFetcher:
    def __init__(self):
        self.resolved_game_date = None

    def get_today_games(self, max_lookahead_days: int = 7):
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(max_lookahead_days):
            check_date = base_date + timedelta(days=day_offset)
            date_str = check_date.strftime('%Y-%m-%d')

            board = scoreboardv2.ScoreboardV2(game_date=date_str)
            df = board.game_header.get_data_frame()

            if not df.empty:
                # Deduplicate by GAME_ID — the API can return the same game twice
                if 'GAME_ID' in df.columns:
                    df = df.drop_duplicates(subset=['GAME_ID'])
                if day_offset == 0:
                    print(f"Found {len(df)} games today ({date_str})")
                else:
                    print(f"No games today. Found {len(df)} games on {date_str} (+{day_offset} day{'s' if day_offset > 1 else ''})")
                self.resolved_game_date = date_str
                return df

            print(f"No games on {date_str}, checking next day...")

        print(f"No games found within the next {max_lookahead_days} days")
        self.resolved_game_date = None
        return pd.DataFrame()

    def get_player_stats(self, player_id, num_games=15, timeout=10):
        log = playergamelog.PlayerGameLog(
            player_id=player_id,
            season='2025-26',
            season_type_all_star='Regular Season',
            timeout=timeout
        )
        
        df = log.get_data_frames()[0]
        
        return df.head(num_games)