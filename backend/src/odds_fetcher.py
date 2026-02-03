"""
Odds Fetcher - Fetches real prop betting lines from odds APIs
Optimized for premium subscription with access to all bookmakers
"""

import requests
from typing import Dict, List, Optional, Any
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone

# loading env vars manually
def load_env_file():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_file()


class OddsFetcher:
    
    MARKET_MAPPING = {
        'player_points': 'PTS',
        'player_assists': 'AST',
        'player_rebounds': 'REB',
        'player_threes': 'FG3M',
        'player_steals': 'STL',
        'player_blocks': 'BLK'
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"
        
    def get_nba_events(self, today_only: bool = True) -> List[Dict]:
        if not self.api_key:
            raise ValueError("API key not set")

        url = f"{self.base_url}/sports/basketball_nba/events"

        params = {
            "apiKey": self.api_key,
            "dateFormat": "iso",
        }

        if today_only:
            ny = ZoneInfo("America/New_York")
            now_ny = datetime.now(ny)

            start_ny = now_ny.replace(hour=0, minute=0, second=0, microsecond=0)
            end_ny = start_ny + timedelta(days=1)

            start_utc = start_ny.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_utc = end_ny.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            params["commenceTimeFrom"] = start_utc
            params["commenceTimeTo"] = end_utc

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            events = response.json()

            if today_only:
                print(f"Found {len(events)} games today (NY date)")
            else:
                print(f"Found {len(events)} upcoming NBA games")

            return events

        except requests.exceptions.RequestException as e:
            print(f"Error fetching events: {e}")
            return []
    
    def get_event_odds(self, event_id: str, markets: List[str]) -> Dict:
        
        if not self.api_key:
            raise ValueError("API key not set")
        url = f"{self.base_url}/sports/basketball_nba/events/{event_id}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': ','.join(markets),
            'oddsFormat': 'american',
            'dateFormat': 'iso'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds for event {event_id}: {e}")
            return {}
    
    def parse_event_props(self, event_data: Dict, event_info: Dict, markets: List[str]) -> Dict[str, Dict]:
        
        player_props = {}
        
        if not event_data or 'bookmakers' not in event_data:
            return player_props
        
        try:
            for bookmaker in event_data['bookmakers']:
                bookmaker_name = bookmaker.get('key', 'unknown')
                
                for market_data in bookmaker.get('markets', []):
                    market_key = market_data.get('key', '')
                    
                    # Verify this is one of the markets we requested
                    if market_key not in markets:
                        continue
                    
                    stat_type = self.MARKET_MAPPING.get(market_key)
                    if not stat_type:
                        continue
                    
                    for outcome in market_data.get('outcomes', []):
                        player_name = outcome.get('description', '')
                        line = outcome.get('point')
                        price = outcome.get('price')
                        name = outcome.get('name', '')
                        
                        if not player_name or line is None:
                            continue
                        
                        if player_name not in player_props:
                            player_props[player_name] = {
                                'event_id': event_info['event_id'],
                                'home_team': event_info['home_team'],
                                'away_team': event_info['away_team'],
                                'commence_time': event_info['commence_time'],
                                'props': {}
                            }
                        
                        if stat_type not in player_props[player_name]['props']:
                            player_props[player_name]['props'][stat_type] = []
                        
                        player_props[player_name]['props'][stat_type].append({
                            'line': float(line),
                            'bookmaker': bookmaker_name,
                            'price': price,
                            'name': name
                        })
        
        except Exception as e:
            print(f"Error parsing props: {e}")
            import traceback
            traceback.print_exc()
        
        return player_props
    
    def get_all_player_props(self, markets: Optional[List[str]] = None) -> Dict[str, Dict]:
        
        if markets is None:
            markets = [
                'player_points',
                'player_assists',
                'player_rebounds',
                'player_threes'
            ]
        
        # Get today's events only
        events = self.get_nba_events(today_only=True)
        if not events:
            print("No events found for today")
            return {}
        
        all_props = {}
        
        # Fetch odds for each event
        for i, event in enumerate(events, 1):
            event_id = event.get('id')
            home_team = event.get('home_team', 'Unknown')
            away_team = event.get('away_team', 'Unknown')
            commence_time = event.get('commence_time', '')
            
            print(f"\n[{i}/{len(events)}] Fetching props for {away_team} @ {home_team}...")
            
            if not event_id:
                continue
            
            event_info = {
                'event_id': event_id,
                'home_team': home_team,
                'away_team': away_team,
                'commence_time': commence_time
            }
            
            event_data = self.get_event_odds(event_id, markets)
            
            # Parse the props with event context
            event_props = self.parse_event_props(event_data, event_info, markets)
            
            print(f"  Found props for {len(event_props)} players")
            
            # Merge into all_props (players should only be in one game)
            for player_name, player_data in event_props.items():
                if player_name in all_props:
                    print(f"  {player_name} appears in multiple games, merging props")
                    for stat_type, lines in player_data['props'].items():
                        if stat_type not in all_props[player_name]['props']:
                            all_props[player_name]['props'][stat_type] = []
                        all_props[player_name]['props'][stat_type].extend(lines)
                else:
                    all_props[player_name] = player_data
            
            # Rate limiting: small delay between requests
            if i < len(events):
                time.sleep(0.5)
        
        return all_props
    
    def get_best_lines(self, player_props: Dict[str, Dict]) -> Dict[str, Dict]:
        
        best_lines = {}
        
        for player_name, player_data in player_props.items():
            best_lines[player_name] = {
                'event_id': player_data.get('event_id'),
                'home_team': player_data.get('home_team'),
                'away_team': player_data.get('away_team'),
                'commence_time': player_data.get('commence_time'),
                'best_lines': {}
            }
            
            props = player_data.get('props', {})
            
            for stat_type, lines in props.items():
                overs = [l for l in lines if l['name'] == 'Over']
                unders = [l for l in lines if l['name'] == 'Under']
                
                best_lines[player_name]['best_lines'][stat_type] = {}
                
                if overs:
                    best_over = min(overs, key=lambda x: x['line'])
                    best_lines[player_name]['best_lines'][stat_type]['over'] = best_over
                
                if unders:
                    best_under = max(unders, key=lambda x: x['line'])
                    best_lines[player_name]['best_lines'][stat_type]['under'] = best_under
        
        return best_lines


class MockOddsFetcher:
    """
    Mock odds fetcher for testing without API key
    Returns estimated lines based on 2024-25 season averages
    """
    
    def get_all_player_props(self) -> Dict[str, Dict]:
        """Returns mock data in the same format as real API with event context"""
        print("Using mock odds data (no API key or using mock mode)")
        
        # Mock event times (today)
        today = datetime.now(timezone.utc).replace(hour=19, minute=0, second=0, microsecond=0)
        
        mock_data = {
            'Stephen Curry': {
                'event_id': 'mock_gsw_lal',
                'home_team': 'Golden State Warriors',
                'away_team': 'Los Angeles Lakers',
                'commence_time': today.isoformat(),
                'props': {
                    'PTS': [
                        {'line': 27.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 27.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'AST': [
                        {'line': 6.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 6.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'REB': [
                        {'line': 4.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 4.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'FG3M': [
                        {'line': 4.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 4.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ]
                }
            },
            'LeBron James': {
                'event_id': 'mock_gsw_lal',
                'home_team': 'Golden State Warriors',
                'away_team': 'Los Angeles Lakers',
                'commence_time': today.isoformat(),
                'props': {
                    'PTS': [
                        {'line': 24.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 24.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'AST': [
                        {'line': 8.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 8.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'REB': [
                        {'line': 7.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 7.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ]
                }
            },
            'Nikola Jokic': {
                'event_id': 'mock_den_bos',
                'home_team': 'Denver Nuggets',
                'away_team': 'Boston Celtics',
                'commence_time': today.replace(hour=22).isoformat(),
                'props': {
                    'PTS': [
                        {'line': 28.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 28.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'AST': [
                        {'line': 9.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 9.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ],
                    'REB': [
                        {'line': 12.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Over'},
                        {'line': 12.5, 'bookmaker': 'draftkings', 'price': -110, 'name': 'Under'},
                    ]
                }
            }
        }
        
        return mock_data
    
    def get_best_lines(self, player_props: Dict) -> Dict:
        """Same implementation as OddsFetcher"""
        fetcher = OddsFetcher()
        return fetcher.get_best_lines(player_props)


def get_odds_fetcher(use_real_api: bool = True):

    api_key = os.getenv('ODDS_API_KEY')
    
    if use_real_api and api_key:
        print("Using Odds API")
        return OddsFetcher(api_key=api_key)
    else:
        print("No API key found")
        return MockOddsFetcher()


def convert_to_simple_format(player_props: Dict[str, Dict]) -> Dict[str, Dict[str, float]]:
    
    simple_props = {}
    
    for player_name, player_data in player_props.items():
        simple_props[player_name] = {}
        
        props = player_data.get('props', {})
        
        for stat_type, lines in props.items():
            # Get all over lines from all bookmakers
            over_lines = [l['line'] for l in lines if l['name'] == 'Over']
            
            if over_lines:
                # Use median line as the consensus
                over_lines.sort()
                median_idx = len(over_lines) // 2
                simple_props[player_name][stat_type] = over_lines[median_idx]
    
    return simple_props


if __name__ == "__main__":    
    fetcher = get_odds_fetcher(use_real_api=True)
    props = fetcher.get_all_player_props()
    
    print(f"RESULTS: Found props for {len(props)} players")
    
    for player_name, player_data in list(props.items())[:3]:
        print(f"\n{player_name}:")
        print(f"  Game: {player_data['away_team']} @ {player_data['home_team']}")
        print(f"  Time: {player_data['commence_time']}")
        print(f"  Event ID: {player_data['event_id']}")
        print(f"  Props:")
        
        for stat_type, lines in player_data['props'].items():
            print(f"    {stat_type}:")
            for line in lines[:3]:  # Show first 3 lines
                print(f"      {line['name']:5} {line['line']:5.1f} @ {line['bookmaker']:15} ({line['price']:+4})")
    
    print("BEST LINES (lowest over, highest under with event context):")
    
    best_lines = fetcher.get_best_lines(props)
    for player_name, player_data in list(best_lines.items())[:3]:
        print(f"\n{player_name}:")
        print(f"  Game: {player_data['away_team']} @ {player_data['home_team']}")
        print(f"  Best Lines:")
        
        for stat_type, directions in player_data['best_lines'].items():
            print(f"    {stat_type}:")
            if 'over' in directions:
                over = directions['over']
                print(f"      Best Over:  {over['line']:5.1f} @ {over['bookmaker']:15} ({over['price']:+4})")
            if 'under' in directions:
                under = directions['under']
                print(f"      Best Under: {under['line']:5.1f} @ {under['bookmaker']:15} ({under['price']:+4})")
    
    print("SIMPLE FORMAT (for analyzer compatibility):")
    
    simple_props = convert_to_simple_format(props)
    for player_name, stats in list(simple_props.items())[:3]:
        print(f"{player_name}: {stats}")
