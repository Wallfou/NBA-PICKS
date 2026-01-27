"""
Test script to verify data fetching and prediction pipeline
Run this to test your complete workflow
"""

from src.fetcher import NBAFetcher
from src.analyzer import NBAAnalyzer
import time

TEST_PLAYERS = {
    'Stephen Curry': 201939,
    'LeBron James': 2544,
    'Nikola Jokic': 203999,
    'Giannis Antetokounmpo': 203507,
    'Luka Doncic': 1629029,
    'Kevin Durant': 201142,
    'Joel Embiid': 203954,
    'Damian Lillard': 203081,
    'Jayson Tatum': 1628369,
    'Anthony Davis': 203076
}

ESTIMATED_PROP_LINES = {
    'Stephen Curry': {'PTS': 27.5, 'AST': 6.5, 'REB': 4.5, 'FG3M': 4.5},
    'LeBron James': {'PTS': 24.5, 'AST': 8.5, 'REB': 7.5},
    'Nikola Jokic': {'PTS': 28.5, 'AST': 9.5, 'REB': 12.5},
    'Giannis Antetokounmpo': {'PTS': 30.5, 'AST': 5.5, 'REB': 11.5},
    'Luka Doncic': {'PTS': 31.5, 'AST': 8.5, 'REB': 8.5},
    'Kevin Durant': {'PTS': 27.5, 'AST': 5.5, 'REB': 6.5},
    'Joel Embiid': {'PTS': 29.5, 'AST': 5.5, 'REB': 10.5},
    'Damian Lillard': {'PTS': 25.5, 'AST': 6.5, 'REB': 4.5},
    'Jayson Tatum': {'PTS': 28.5, 'AST': 5.5, 'REB': 8.5},
    'Anthony Davis': {'PTS': 26.5, 'AST': 3.5, 'REB': 11.5}
}


def test_single_player(player_name: str):
    print(f"Testing: {player_name}")
    
    fetcher = NBAFetcher()
    analyzer = NBAAnalyzer(num_games=10)
    
    player_id = TEST_PLAYERS[player_name]
    
    try:
        print(f"Fetching game logs for {player_name} ID: {player_id}")
        game_logs = fetcher.get_player_stats(player_id, num_games=15)
        
        print(f"Successfully fetched {len(game_logs)} games")
        print(f"\nRecent stats preview: ")
        print(game_logs[['GAME_DATE', 'PTS', 'AST', 'REB']].head(10))
        
        prop_lines = ESTIMATED_PROP_LINES.get(player_name, {'PTS': 25.5})
        
        print(f"\nAnalyzing props with lines: {prop_lines}")
        predictions = analyzer.analyze_player(game_logs, player_name, prop_lines)
        
        print("PREDICTIONS:")
        
        for pred in predictions:
            print(f"\n{analyzer.generate_picks(pred)}")
        return predictions
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def test_multiple_players():
    print("TESTING PLAYERS - GENERATING TOP 5 PICKS")
    
    fetcher = NBAFetcher()
    analyzer = NBAAnalyzer(num_games=10)
    
    all_predictions = []
    
    players_to_test = list(TEST_PLAYERS.items())[:5]
    
    for player_name, player_id in players_to_test:
        try:
            print(f"\nFetching {player_name}")
            game_logs = fetcher.get_player_stats(player_id, num_games=15)
            
            prop_lines = ESTIMATED_PROP_LINES.get(player_name, {'PTS': 25.5})
            predictions = analyzer.analyze_player(game_logs, player_name, prop_lines)
            
            all_predictions.extend(predictions)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error with {player_name}: {str(e)}")
            continue
    
    print(f"TOP 5 MOST CONFIDENT PICKS")
    
    top_picks = analyzer.rank_picks(all_predictions, min_confidence=60.0, top_n=5)
    
    for i, pick in enumerate(top_picks, 1):
        print(f"\n#{i}")
        print(analyzer.generate_picks(pick))
    
    return top_picks


def test_today_games():
    print("TESTING: FETCH TODAY'S GAMES")
    
    fetcher = NBAFetcher()
    
    try:
        games_df = fetcher.get_today_games()
        
        print(f"\nFound {len(games_df)} games today")
        
        if len(games_df) > 0:
            print("\nToday's Games:")
            print(games_df[['GAME_DATE_EST', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID', 'GAME_STATUS_TEXT']].head(10))
        else:
            print("\nNo games scheduled for today")
            
    except Exception as e:
        print(f"Error fetching games: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    test_today_games()
    
    test_single_player('Stephen Curry')
    
    test_multiple_players()

if __name__ == "__main__":
    main()