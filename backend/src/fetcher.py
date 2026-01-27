import requests
import pandas as pd
from datetime import datetime

class NBAFetcher:
    BASE_URL = "https://stats.nba.com/stats"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://stats.nba.com/'
        }

    def get_today_games(self):
        url = f"{self.BASE_URL}/scoreboardv2"
        params = {
            'GameDate': datetime.now().strftime('%m/%d/%Y'), 
            'DayOffset': 0,
            'LeagueID': '00',
        }
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    ## Get the last 15 games for a player, transformed json response into pandas dataframe
    def get_player_stats(self, player_id, num_games=15):
        url = f"{self.BASE_URL}/playergamelog"
        params = {
            'PlayerID': player_id,
            'Season': '2024-25',
            'SeasonType': 'Regular Season'
        }
        response = requests.get(url, headers=self.headers, params=params)
        data = response.json()
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet'][:num_games]
        return pd.DataFrame(rows, columns=headers)

