"""
Production Flask API for NBA Props Predictor
Integrated with premium odds API fetcher
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from src.fetcher import NBAFetcher
from src.analyzer import NBAAnalyzer
from src.odds_fetcher import get_odds_fetcher, convert_to_simple_format
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
import os

app = Flask(__name__)
CORS(app)

# helper for sanitizing numeric values
import math
def safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default 

# Initialize services
print("Initializing NBA Props Predictor services...")

try:
    fetcher = NBAFetcher()
    print("NBAFetcher initialized")
except Exception as e:
    print(f"Failed to initialize NBAFetcher: {e}")
    raise

try:
    analyzer = NBAAnalyzer(num_games=10)
    print("NBAAnalyzer initialized")
except Exception as e:
    print(f"Failed to initialize NBAAnalyzer: {e}")
    raise

USE_REAL_ODDS = os.getenv('USE_REAL_ODDS', 'false').lower() == 'true'

try:
    odds_fetcher = get_odds_fetcher(use_real_api=USE_REAL_ODDS)
    print(f"OddsFetcher initialized (mode: {'REAL API' if USE_REAL_ODDS else 'MOCK'})")
except Exception as e:
    print(f"Failed to initialize OddsFetcher: {e}")
    raise

print("All services initialized successfully!\n")

# cache for 6 hours — Odds API tokens are limited
picks_cache = {
    'data': None,
    'raw_odds': None,
    'timestamp': None,
    'ttl': 21600
}

# cache for 40 minutes
games_cache = {
    'data': None,
    'date': None,
    'timestamp': None,
    'ttl': 2400
}

# cache for 24 hours
players_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 86400
}


def get_player_id_mapping():
    """
    Create mapping of player names to IDs from odds data
    This helps match odds API names with NBA API data (will expand later to reduce api calls)
    """
    KNOWN_PLAYERS = {
        'Stephen Curry': 201939,
        'LeBron James': 2544,
        'Nikola Jokic': 203999,
        'Giannis Antetokounmpo': 203507,
        'Luka Doncic': 1629029,
        'Kevin Durant': 201142,
        'Joel Embiid': 203954,
        'Damian Lillard': 203081,
        'Jayson Tatum': 1628369,
        'Anthony Davis': 203076,
        'Devin Booker': 1626164,
        'Shai Gilgeous-Alexander': 1628983,
        'Donovan Mitchell': 1628378,
        'Tyrese Maxey': 1630178,
        "De'Aaron Fox": 1628368,
        'Trae Young': 1629027,
        'Karl-Anthony Towns': 1626157,
        'Pascal Siakam': 1627783,
        'Julius Randle': 203944,
        'Jalen Brunson': 1628973,
        'Anthony Edwards': 1630162,
        'Ja Morant': 1629630,
        'Jimmy Butler': 202710,
        'Kawhi Leonard': 202695,
        'Paul George': 202331,
        'Kyrie Irving': 202681,
        'Bam Adebayo': 1628389,
        'Bradley Beal': 203078,
        'Zion Williamson': 1629627,
        'Brandon Ingram': 1627742,
        'Egot Demin': 183714,

    }
    return KNOWN_PLAYERS


def fetch_player_id_from_nba_api(player_name: str):
    """
    Fallback: try to find player id with nba api
    """
    try:
        from nba_api.stats.static import players
        all_players = players.get_active_players()
        
        for player in all_players:
            if player['full_name'].lower() == player_name.lower():
                return player['id']
        
        # fuzzy match
        last_name = player_name.split()[-1].lower()
        for player in all_players:
            if last_name in player['full_name'].lower():
                return player['id']
        
        return None
    except ImportError:
        print(f"nba_api package not installed. Cannot lookup player {player_name}")
        return None
    except Exception as e:
        print(f"Error looking up player {player_name}: {e}")
        return None


def generate_all_picks(force_refresh: bool = False):
    """
    Generate picks for all players with odds today
    """
    if not force_refresh and picks_cache['data'] and picks_cache['timestamp']:
        age = (datetime.now() - picks_cache['timestamp']).total_seconds()
        if age < picks_cache['ttl']:
            print(f"Using cached picks with age: {int(age)}s")
            return picks_cache['data'], picks_cache['raw_odds']
    
    print("GENERATING FRESH PICKS")
    start_time = time.time()
    
    print("\nFetching prop lines from Odds API...")
    raw_odds = odds_fetcher.get_all_player_props()
    print(f"Found odds for {len(raw_odds)} players")
    
    picks_cache['raw_odds'] = raw_odds
    
    simple_props = convert_to_simple_format(raw_odds)
    
    if not simple_props:
        print("No prop lines available, cant convert to simple format")
        return [], raw_odds
    
    print("\nMapping player names to IDs...")
    player_id_map = get_player_id_mapping()

    # Resolve player IDs (mostly dict lookup, sequential and fast)
    resolved = {}   # player_name -> (player_id, prop_lines)
    skipped_no_id = []
    for player_name, prop_lines in simple_props.items():
        player_id = player_id_map.get(player_name)
        if not player_id:
            player_id = fetch_player_id_from_nba_api(player_name)
            if player_id:
                player_id_map[player_name] = player_id
        if player_id:
            resolved[player_name] = (player_id, prop_lines)
        else:
            skipped_no_id.append(player_name)

    for name in skipped_no_id[:5]:
        print(f"skipping {name} (cannot find player id)")

    # Fetch all game logs in parallel with a short timeout
    print(f"\nFetching game logs for {len(resolved)} players in parallel...")

    def _fetch_logs(item):
        pname, (pid, _) = item
        try:
            time.sleep(0.6)
            logs = fetcher.get_player_stats(pid, num_games=15, timeout=30)
            return pname, logs, None
        except Exception as exc:
            return pname, None, exc

    game_log_map = {}   # player_name -> DataFrame | None
    error_map = {}      # player_name -> exception

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_fetch_logs, item): item[0] for item in resolved.items()}
        for future in as_completed(futures):
            pname, logs, exc = future.result()
            if exc is not None:
                error_map[pname] = exc
            else:
                game_log_map[pname] = logs

    # Generate predictions (pure computation, no more NBA API calls)
    print("\nAnalyzing confidence...")
    all_predictions = []
    analyzed_count = 0
    error_count = len(error_map)
    skipped_count = len(skipped_no_id)

    for player_name, (player_id, prop_lines) in resolved.items():
        if player_name in error_map:
            print(f"Error analyzing {player_name}: {error_map[player_name]}")
            continue

        game_logs = game_log_map.get(player_name)
        if game_logs is None or len(game_logs) < 5:
            skipped_count += 1
            if skipped_count <= 5:
                n = len(game_logs) if game_logs is not None else 0
                print(f"skipping {player_name} (insufficient games: {n})")
            continue

        try:
            predictions = analyzer.analyze_player(
                game_logs=game_logs,
                player_name=player_name,
                prop_lines=prop_lines
            )

            if player_name in raw_odds:
                event_info = raw_odds[player_name]
                for pred in predictions:
                    pred['event_id'] = event_info.get('event_id', 'N/A')
                    pred['home_team'] = event_info.get('home_team', 'N/A')
                    pred['away_team'] = event_info.get('away_team', 'N/A')
                    pred['commence_time'] = event_info.get('commence_time', 'N/A')

            all_predictions.extend(predictions)
            analyzed_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error generating predictions for {player_name}: {e}")
    
    elapsed = time.time() - start_time
    print(f"Successfully analyzed: {analyzed_count} players")
    print(f"Skipped: {skipped_count} players")
    print(f"Errors: {error_count}")
    print(f"Total predictions generated: {len(all_predictions)}")
    print(f"Time taken: {elapsed:.1f}s")
    
    # Cache the results
    picks_cache['data'] = all_predictions
    picks_cache['timestamp'] = datetime.now()
    
    return all_predictions, raw_odds


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'NBA Props Predictor API',
        'version': '2.0.0',
        'using_real_odds': USE_REAL_ODDS,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/health')
def health():
    """Detailed health check"""
    cache_age = None
    if picks_cache['timestamp']:
        cache_age = int((datetime.now() - picks_cache['timestamp']).total_seconds())
    
    return jsonify({
        'status': 'healthy',
        'services': {
            'fetcher': 'active',
            'analyzer': 'active',
            'odds_api': 'real' if USE_REAL_ODDS else 'mock'
        },
        'cache': {
            'has_data': picks_cache['data'] is not None,
            'predictions_count': len(picks_cache['data']) if picks_cache['data'] else 0,
            'age_seconds': cache_age,
            'ttl_seconds': picks_cache['ttl']
        },
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/picks/top')
def get_top_picks():
    """
    Get top picks across all players with odds
    """
    try:
        stat_type = request.args.get('stat_type', None)
        min_confidence = float(request.args.get('min_confidence', 65.0))
        limit = int(request.args.get('limit', 5))
        pick_type = request.args.get('pick_type', None)
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        all_predictions, raw_odds = generate_all_picks(force_refresh=force_refresh)
        
        filtered = all_predictions
        
        if stat_type:
            filtered = [p for p in filtered if p['stat_type'] == stat_type]
        
        if pick_type:
            filtered = [p for p in filtered if p['pick'] == pick_type.upper()]
        
        top_picks = analyzer.rank_picks(filtered, min_confidence=min_confidence, top_n=limit)
        
        return jsonify({
            'success': True,
            'count': len(top_picks),
            'total_analyzed': len(all_predictions),
            'picks': top_picks,
            'filters': {
                'stat_type': stat_type,
                'pick_type': pick_type,
                'min_confidence': min_confidence,
                'limit': limit
            },
            'cache_age_seconds': int((datetime.now() - picks_cache['timestamp']).total_seconds()) if picks_cache['timestamp'] else None,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/picks/player/<player_name>')
def get_player_picks(player_name):
    """Get predictions for a specific player"""
    try:
        all_predictions, raw_odds = generate_all_picks()
        
        player_picks = [p for p in all_predictions if p['player_name'].lower() == player_name.lower()]
        
        if not player_picks:
            return jsonify({
                'success': False,
                'error': f'No predictions found for {player_name}. Player may not have odds today or had insufficient game data.'
            }), 404
        
        event_info = {}
        if player_picks:
            event_info = {
                'event_id': player_picks[0].get('event_id', 'N/A'),
                'home_team': player_picks[0].get('home_team', 'N/A'),
                'away_team': player_picks[0].get('away_team', 'N/A'),
                'commence_time': player_picks[0].get('commence_time', 'N/A')
            }
        
        return jsonify({
            'success': True,
            'player': player_name,
            'event_info': event_info,
            'predictions': player_picks,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/games/today')
def get_today_games():
    """Get next available NBA games (today or nearest future date with games)"""
    try:
        if games_cache['data'] and games_cache['timestamp']:
            age = (datetime.now() - games_cache['timestamp']).total_seconds()
            if age < games_cache['ttl']:
                print(f"Using cached games (age: {int(age)}s)")
                return jsonify({
                    'success': True,
                    'count': len(games_cache['data']),
                    'games': games_cache['data'],
                    'date': games_cache['date']
                })

        games_df = fetcher.get_today_games()
        games = games_df.to_dict('records')
        resolved_date = fetcher.resolved_game_date or datetime.now().strftime('%Y-%m-%d')

        games_cache['data'] = games
        games_cache['date'] = resolved_date
        games_cache['timestamp'] = datetime.now()
        
        return jsonify({
            'success': True,
            'count': len(games),
            'games': games,
            'date': resolved_date
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _filter_players_today(players: list) -> list:
    """Return only players who have prop lines available for today."""
    raw_odds = picks_cache.get('raw_odds')
    if not raw_odds:
        try:
            raw_odds = odds_fetcher.get_all_player_props()
        except Exception:
            return players

    if not raw_odds:
        return players

    today_names = {name.lower() for name in raw_odds}
    return [p for p in players if p['name'].lower() in today_names]


@app.route('/api/allPlayers')
def get_players():
    """Get all active NBA players with stats (cached 24h)"""
    try:
        today_only = request.args.get('today_only', 'false').lower() == 'true'

        if players_cache['data'] and players_cache['timestamp']:
            age = (datetime.now() - players_cache['timestamp']).total_seconds()
            if age < players_cache['ttl']:
                print(f"Using cached players (age: {int(age)}s)")
                players = players_cache['data']
                if today_only:
                    players = _filter_players_today(players)
                return jsonify({
                    'success': True,
                    'count': len(players),
                    'players': players
                })

        from nba_api.stats.endpoints import playerindex

        print("Fetching player index from NBA API...")
        df = None
        for attempt in range(3):
            try:
                idx = playerindex.PlayerIndex(season='2025-26', league_id='00', timeout=30)
                df = idx.get_data_frames()[0]
                break
            except Exception as e:
                print(f"PlayerIndex attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)
        if df is None:
            return jsonify({'success': False, 'error': 'API unavailable, try again'}), 503

        # Keep only active roster players
        df = df[df['ROSTER_STATUS'] == 1].copy()

        players = []
        for _, row in df.iterrows():
            players.append({
                'id': int(row['PERSON_ID']),
                'name': f"{row['PLAYER_FIRST_NAME']} {row['PLAYER_LAST_NAME']}",
                'team': str(row.get('TEAM_ABBREVIATION', '') or ''),
                'jersey': '' if str(row.get('JERSEY_NUMBER', '')).lower() == 'nan' else str(row.get('JERSEY_NUMBER', '')),
                'position': str(row.get('POSITION', '') or ''),
                'pts': round(safe_float(row.get('PTS'), 0.0), 1),
                'reb': round(safe_float(row.get('REB'), 0.0), 1),
                'ast': round(safe_float(row.get('AST'), 0.0), 1),
            })

        players.sort(key=lambda p: p['name'])

        players_cache['data'] = players
        players_cache['timestamp'] = datetime.now()

        filtered = _filter_players_today(players) if today_only else players
        print(f"Fetched {len(players)} active players ({len(filtered)} playing today)" if today_only else f"Fetched {len(players)} active players")
        return jsonify({
            'success': True,
            'count': len(filtered),
            'players': filtered
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/odds/players')
def get_odds_players():
    """Get list of players who have odds available today"""
    try:
        _, raw_odds = generate_all_picks()
        
        players_info = []
        for player_name, player_data in raw_odds.items():
            players_info.append({
                'player_name': player_name,
                'home_team': player_data.get('home_team', 'N/A'),
                'away_team': player_data.get('away_team', 'N/A'),
                'commence_time': player_data.get('commence_time', 'N/A'),
                'stats_available': list(player_data.get('props', {}).keys())
            })
        
        return jsonify({
            'success': True,
            'count': len(players_info),
            'players': players_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/picks/refresh', methods=['POST'])
def refresh_picks():
    """Force refresh the picks cache"""
    try:
        print("\nManual refresh triggered via API")
        all_predictions, raw_odds = generate_all_picks(force_refresh=True)
        
        return jsonify({
            'success': True,
            'message': 'Picks refreshed successfully',
            'total_predictions': len(all_predictions),
            'players_with_odds': len(raw_odds),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats/summary')
def get_stats_summary():
    """Get summary statistics about current picks"""
    try:
        all_predictions, raw_odds = generate_all_picks()
        
        if not all_predictions:
            return jsonify({
                'success': True,
                'message': 'No predictions available'
            })
        
        total_picks = len(all_predictions)
        avg_confidence = sum(p['confidence'] for p in all_predictions) / total_picks
        
        stat_breakdown = {}
        for pred in all_predictions:
            stat = pred['stat_type']
            stat_breakdown[stat] = stat_breakdown.get(stat, 0) + 1
        
        pick_breakdown = {}
        for pred in all_predictions:
            pick = pred['pick']
            pick_breakdown[pick] = pick_breakdown.get(pick, 0) + 1
        
        high_confidence = len([p for p in all_predictions if p['confidence'] >= 75])
        medium_confidence = len([p for p in all_predictions if 65 <= p['confidence'] < 75])
        
        return jsonify({
            'success': True,
            'summary': {
                'total_picks': total_picks,
                'players_analyzed': len(raw_odds),
                'average_confidence': round(avg_confidence, 1),
                'high_confidence_picks': high_confidence,
                'medium_confidence_picks': medium_confidence,
                'stat_breakdown': stat_breakdown,
                'pick_breakdown': pick_breakdown
            },
            'cache_age': int((datetime.now() - picks_cache['timestamp']).total_seconds()) if picks_cache['timestamp'] else None,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)