import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as NBA_LOGOS from '../components/nbaLogos';
import './Picks.css';


const TEAM_LOGO = ({ abbr, size }: { abbr: string; size: number }) => {
  const Logo = (
    NBA_LOGOS as Record<string, React.ComponentType<{ size: number }>>
  )[abbr];
  if (!Logo) return null;
  return <Logo size={size} />;
};

interface Prediction {
  stat_type: string;
  pick: 'OVER' | 'UNDER';
  confidence: number;
  line: number;
  average: number;
  last_5_avg: number;
  hit_rate: number;
  std_dev: number;
  trend: 'up' | 'down' | 'neutral';
  recent_games: number[];
  home_team: string;
  away_team: string;
  commence_time: string;
}

interface PlayerPicksData {
  player: string;
  event_info: {
    home_team: string;
    away_team: string;
    commence_time: string;
  };
  predictions: Prediction[];
}

interface TopPicksData {
  count: number;
  total_analyzed: number;
  picks: (Prediction & { player_name: string })[];
  cache_age_seconds: number | null;
}

interface BarChartProps {
  values: number[];
  line: number;
  pick: 'OVER' | 'UNDER';
}

const BarChart: React.FC<BarChartProps> = ({ values, line, pick }) => {
  // values come in most-recent-first; reverse so chart reads oldest→newest
  const games = [...values].reverse();
  const [hover, setHover] = useState<null | { i: number, x: number; y: number }>(null);

  const W = 500;
  const H = 150;
  const PAD = { top: 16, right: 32, bottom: 24, left: 32 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const max = Math.max(...games, line) * 1.2;
  const barW = chartW / games.length;
  const barGap = barW * 0.2;
  const effectiveBarW = barW - barGap;

  const yScale = (v: number) => chartH - (v / max) * chartH;
  const lineY = yScale(line);

  const isHit = (v: number) => pick === 'OVER' ? v > line : v < line;

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} className="picks-chart" aria-hidden="true" onMouseLeave={() => setHover(null)}>
        
        {/* Y-axis label ticks */}
        {[0, 0.5, 1].map((pct) => {
          const val = max * pct;
          const y = PAD.top + yScale(val);
          return (
            <g key={pct}>
              <line
                x1={PAD.left} y1={y}
                x2={PAD.left + chartW} y2={y}
                stroke="rgba(255, 255, 255, 0.22)" strokeWidth={1}
              />
              <text
                x={PAD.left - 4} y={y + 4}
                textAnchor="end"
                fontSize={8}
                fill="#555"
              >
                {Math.round(val)}
              </text>
            </g>
          );
        })}

        {/* Bars */}
        {games.map((v, i) => {
          const x = PAD.left + i * barW + barGap / 2;
          const barH = (v / max) * chartH;
          const y = PAD.top + chartH - barH;
          const hit = isHit(v);

          return (
            <g key={i}>
              <rect
                x={x} 
                y={y}
                width={effectiveBarW} 
                height={barH}
                rx={2}
                fill={hit ? 'rgba(51,143,74,0.75)' : 'rgba(200,60,60,0.65)'}
                onMouseMove={(e) => {
                  const wrap = e.currentTarget.ownerSVGElement!;
                  const r = wrap.getBoundingClientRect();
                  setHover({ i, x: e.clientX - r.left, y: e.clientY - r.top });
                }}
              />
              <text
                x={x + effectiveBarW / 2}
                y={PAD.top + chartH + 13}
                textAnchor="middle"
                fontSize={9}
                fill="#444"
              >
                G{i + 1}
              </text>
            </g>
          );
        })}

        {/* Prop line */}
        <line
          x1={PAD.left} y1={PAD.top + lineY}
          x2={PAD.left + chartW} y2={PAD.top + lineY}
          stroke="#338f4a" strokeWidth={1.5}
          strokeDasharray="5 3"
        />
        <text
          x={PAD.left + chartW + 4}
          y={PAD.top + lineY + 4}
          fontSize={9}
          fill="#338f4a"
        >
          {line}
        </text>
      </svg>

      {hover && (
        <div 
          style={{ 
            position: "absolute",
            left: hover.x + 13,
            top: hover.y - 10,
            background: "rgba(10,10,10,0.92)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 10,
            padding: "8px 10px",
            color: "#fff",
            fontSize: 13,
            pointerEvents: "none",
            whiteSpace: "nowrap", 
          }}>
            <div style={{ fontWeight: 800, marginBottom: 4}}>G{hover.i + 1}</div>
            <div>Value: <b>{games[hover.i]}</b></div>
            <div>Line: <b>{line}</b></div>
            <div>Result:{" "}
              <b style={{ color: isHit(games[hover.i]) ? "#4cbe6c" : "#e06060" }}>
                {isHit(games[hover.i]) ? "HIT" : "MISS"}
              </b>
            </div>
          </div>
        )}
    </div>
  );
};

const TrendBadge: React.FC<{ trend: string }> = ({ trend }) => {
  const map: Record<string, { label: string; cls: string }> = {
    up: { label: '▲ Trending up', cls: 'trend-up' },
    down: { label: '▼ Trending down', cls: 'trend-down' },
    neutral: { label: '— Neutral', cls: 'trend-neutral' },
  };
  const t = map[trend] ?? map.neutral;
  return <span className={`trend-badge ${t.cls}`}>{t.label}</span>;
};

const fmt = (v: number) => (v != null && !isNaN(v) ? v.toFixed(1) : '—');

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
    });
  } catch {
    return iso;
  }
};

const STAT_LABELS: Record<string, string> = {
  PTS: 'Points', REB: 'Rebounds', AST: 'Assists',
  BLK: 'Blocks', STL: 'Steals', FG3M: '3-Pointers',
};


const Picks = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const navigate = useNavigate();

  const decoded = playerName ? decodeURIComponent(playerName) : null;

  const [data, setData] = useState<PlayerPicksData | null>(null);
  const [loading, setLoading] = useState(!!decoded);
  const [error, setError] = useState<string | null>(null);
  const [playerId, setPlayerId] = useState<number | null>(null);

  const [topPicks, setTopPicks] = useState<TopPicksData | null>(null);
  const [topLoading, setTopLoading] = useState(!decoded);
  const [topError, setTopError] = useState<string | null>(null);
  const [playerIds, setPlayerIds] = useState<Record<string, number>>({});

  // Fetch player IDs for headshots (shared, from already-cached /api/players)
  useEffect(() => {
    fetch('http://localhost:5001/api/allPlayers')
      .then((r) => r.json())
      .then((d) => {
        if (!d.success) return;
        const map: Record<string, number> = {};
        for (const p of d.players as { name: string; id: number }[]) {
          map[p.name.toLowerCase()] = p.id;
        }
        setPlayerIds(map);
        if (decoded) {
          const id = map[decoded.toLowerCase()];
          if (id) setPlayerId(id);
        }
      })
      .catch(() => {});
  }, [decoded]);

  // Fetch top 5 picks when on /picks (no player param)
  useEffect(() => {
    if (decoded) return;
    fetch('http://localhost:5001/api/picks/top?limit=5&min_confidence=65')
      .then((r) => r.json())
      .then((d) => {
        if (d.success) setTopPicks(d);
        else setTopError(d.error || 'Could not load top picks.');
      })
      .catch((e) => setTopError(e instanceof Error ? e.message : 'Could not connect to the server'))
      .finally(() => setTopLoading(false));
  }, [decoded]);

  // Fetch picks
  useEffect(() => {
    if (!decoded) return;

    fetch(`http://localhost:5001/api/picks/player/${encodeURIComponent(decoded)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success) {
          setData(d);
        } else {
          setError(d.error || 'No picks found for this player.');
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not connect to the server'))
      .finally(() => setLoading(false));
  }, [decoded]);

  if (!decoded) {
    if (topLoading) {
      return (
        <div className="picks-page">
          <div className="picks-loading">Loading top picks…</div>
        </div>
      );
    }
    if (topError || !topPicks) {
      return (
        <div className="picks-page">
          <div className="picks-error"><span>{topError ?? 'No picks available.'}</span></div>
        </div>
      );
    }

    return (
      <div className="picks-page">
        <div className="picks-top-header">
          <h1>Top Picks For Today</h1>
          <p className="picks-top-subtitle">
            {topPicks.count} picks · {topPicks.total_analyzed} players analyzed
            {topPicks.cache_age_seconds != null && (
              <span className="picks-cache-age"> · cached {Math.round(topPicks.cache_age_seconds / 60)}m ago</span>
            )}
          </p>
        </div>

        <div className="picks-stats">
          {topPicks.picks.map((pred, i) => {
            const pid = playerIds[pred.player_name.toLowerCase()];
            return (
              <div
                key={i}
                className="picks-stat-card picks-stat-card--clickable"
                onClick={() => navigate(`/picks/${encodeURIComponent(pred.player_name)}`)}
              >
                {/* Player row */}
                <div className="picks-top-player-row">
                  {pid && (
                    <img
                      className="picks-top-headshot"
                      src={`https://cdn.nba.com/headshots/nba/latest/260x190/${pid}.png`}
                      alt={pred.player_name}
                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                    />
                  )}
                  <div className="picks-top-player-info">
                    <span className="picks-top-player-name">{pred.player_name}</span>
                    <span className="picks-top-game">
                      {pred.away_team} @ {pred.home_team} · {formatTime(pred.commence_time)}
                    </span>
                  </div>
                  <span className="picks-top-rank">#{i + 1}</span>
                </div>

                {/* Stat header */}
                <div className="picks-stat-header">
                  <span className="picks-stat-type">
                    {STAT_LABELS[pred.stat_type] ?? pred.stat_type}
                  </span>
                  <div className="picks-stat-line-group">
                    <span className="picks-line">{pred.line} {pred.stat_type}</span>
                    <span className={`picks-pick picks-pick-${pred.pick.toLowerCase()}`}>
                      {pred.pick}
                    </span>
                  </div>
                  <div className="picks-confidence-group">
                    <span className="picks-confidence-label">Confidence</span>
                    <span className="picks-confidence-value">{pred.confidence}%</span>
                    <div className="picks-confidence-bar">
                      <div className="picks-confidence-fill" style={{ width: `${pred.confidence}%` }} />
                    </div>
                  </div>
                </div>

                <BarChart values={pred.recent_games} line={pred.line} pick={pred.pick} />

                <div className="picks-secondary">
                  <div className="picks-sec-stat">
                    <span className="picks-sec-val">{fmt(pred.average)}</span>
                    <span className="picks-sec-label">Season Avg</span>
                  </div>
                  <div className="picks-sec-stat">
                    <span className="picks-sec-val">{fmt(pred.last_5_avg)}</span>
                    <span className="picks-sec-label">L5 Avg</span>
                  </div>
                  <div className="picks-sec-stat">
                    <span className="picks-sec-val">{pred.hit_rate}%</span>
                    <span className="picks-sec-label">Hit Rate</span>
                  </div>
                  <div className="picks-sec-stat">
                    <span className="picks-sec-val">{fmt(pred.std_dev)}</span>
                    <span className="picks-sec-label">Std Dev</span>
                  </div>
                  <TrendBadge trend={pred.trend} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="picks-page">
        <div className="picks-loading">Loading picks for {decoded}…</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="picks-page">
        <button className="picks-back" onClick={() => navigate('/players')}>
          ← Back to Players
        </button>
        <div className="picks-error">
          <span>{error ?? 'No data available.'}</span>
        </div>
      </div>
    );
  }

  const { event_info, predictions } = data;
  const statOrder = ['PTS', 'REB', 'AST', 'FG3M', 'BLK', 'STL'];
  const sorted = [...predictions].sort(
    (a, b) => statOrder.indexOf(a.stat_type) - statOrder.indexOf(b.stat_type)
  );

  // Determine which team the player is on from the raw_odds data
  // Use away_team from first prediction (the player plays in this game)
  const awayTeam = event_info.away_team;
  const homeTeam = event_info.home_team;

  return (
    <div className="picks-page">
      <button className="picks-back" onClick={() => navigate('/players')}>
        ← Back to Players
      </button>

      {/* Player header */}
      <div className="picks-header">
        <div className="picks-player-identity">
          {playerId && (
            <img
              className="picks-headshot"
              src={`https://cdn.nba.com/headshots/nba/latest/260x190/${playerId}.png`}
              alt={decoded}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <div className="picks-player-info">
            <h1>{decoded}</h1>
            {event_info.commence_time !== 'N/A' && (
              <div className="picks-game-info">
                <div className="picks-matchup">
                  <TEAM_LOGO abbr={awayTeam.split(' ').pop()!.toUpperCase()} size={28} />
                  <span className="picks-matchup-teams">{awayTeam} @ {homeTeam}</span>
                  <TEAM_LOGO abbr={homeTeam.split(' ').pop()!.toUpperCase()} size={28} />
                </div>
                <p className="picks-game-time">{formatTime(event_info.commence_time)}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Stat cards */}
      <div className="picks-stats">
        {sorted.map((pred) => (
          <div key={pred.stat_type} className="picks-stat-card">
            {/* Card header */}
            <div className="picks-stat-header">
              <span className="picks-stat-type">
                {STAT_LABELS[pred.stat_type] ?? pred.stat_type}
              </span>
              <div className="picks-stat-line-group">
                <span className="picks-line">{pred.line} {pred.stat_type}</span>
                <span className={`picks-pick picks-pick-${pred.pick.toLowerCase()}`}>
                  {pred.pick}
                </span>
              </div>
              <div className="picks-confidence-group">
                <span className="picks-confidence-label">Confidence</span>
                <span className="picks-confidence-value">{pred.confidence}%</span>
                <div className="picks-confidence-bar">
                  <div
                    className="picks-confidence-fill"
                    style={{ width: `${pred.confidence}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Bar chart */}
            <BarChart
              values={pred.recent_games}
              line={pred.line}
              pick={pred.pick}
            />

            {/* Secondary stats */}
            <div className="picks-secondary">
              <div className="picks-sec-stat">
                <span className="picks-sec-val">{fmt(pred.average)}</span>
                <span className="picks-sec-label">Season Avg</span>
              </div>
              <div className="picks-sec-stat">
                <span className="picks-sec-val">{fmt(pred.last_5_avg)}</span>
                <span className="picks-sec-label">L5 Avg</span>
              </div>
              <div className="picks-sec-stat">
                <span className="picks-sec-val">{pred.hit_rate}%</span>
                <span className="picks-sec-label">Hit Rate</span>
              </div>
              <div className="picks-sec-stat">
                <span className="picks-sec-val">{fmt(pred.std_dev)}</span>
                <span className="picks-sec-label">Std Dev</span>
              </div>
              <TrendBadge trend={pred.trend} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Picks;
