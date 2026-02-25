import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import * as NBA_LOGOS from "../components/nbaLogos";
import "./Players.css";

const TEAM_LOGO = ({ abbr, size }: { abbr: string; size: number }) => {
  const Logo = (
    NBA_LOGOS as Record<string, React.ComponentType<{ size: number }>>
  )[abbr];
  if (!Logo) return null;
  return <Logo size={size} />;
};

const HEADSHOT_URL = (id: number) =>
  `https://cdn.nba.com/headshots/nba/latest/260x190/${id}.png`;

interface Player {
  id: number;
  name: string;
  team: string;
  jersey: string;
  position: string;
  pts: number;
  reb: number;
  ast: number;
  has_picks: boolean;
}

const fmt = (v: number) => (v != null && !isNaN(v) ? v.toFixed(1) : "—");

const POSITION_ORDER = ["PG", "SG", "SF", "PF", "C"];

const Players = () => {
  const navigate = useNavigate();
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const [selectedTeams, setSelectedTeams] = useState<Set<string>>(new Set());
  const [selectedPositions, setSelectedPositions] = useState<Set<string>>(new Set());
  const [minPts, setMinPts] = useState<string>("");
  const [maxPts, setMaxPts] = useState<string>("");

  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetchPlayers = async () => {
      try {
        const res = await fetch("http://localhost:5001/api/allPlayers?today_only=true");
        const data = await res.json();
        if (data.success) {
          setPlayers(data.players);
        } else {
          setError(data.error || "Failed to fetch players");
        }
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Could not connect to the server",
        );
      } finally {
        setLoading(false);
      }
    };
    fetchPlayers();
  }, [retryKey]);

  const allTeams = useMemo(
    () => [...new Set(players.map((p) => p.team).filter(Boolean))].sort(),
    [players],
  );

  const allPositions = useMemo(() => {
    const raw = [...new Set(players.map((p) => p.position).filter(Boolean))];
    return raw.sort(
      (a, b) => (POSITION_ORDER.indexOf(a) ?? 99) - (POSITION_ORDER.indexOf(b) ?? 99),
    );
  }, [players]);

  const toggleTeam = (team: string) =>
    setSelectedTeams((prev) => {
      const next = new Set(prev);
      if (next.has(team)) { 
        next.delete(team); 
      } 
      else { 
        next.add(team); 
      }
      return next;
    });

  const togglePosition = (pos: string) =>
    setSelectedPositions((prev) => {
      const next = new Set(prev);
      if (next.has(pos)) { 
        next.delete(pos); 
      } 
      else { 
        next.add(pos); 
      }
      return next;
    });
  
  const clearFilters = () => {
    setSelectedTeams(new Set());
    setSelectedPositions(new Set());
    setMinPts("");
    setMaxPts("");
    setSearch("");
  };

  const minPtsNum = minPts.trim() !== "" ? parseFloat(minPts) : null;
  const maxPtsNum = maxPts.trim() !== "" ? parseFloat(maxPts) : null;

  const hasActiveFilters =
    selectedTeams.size > 0 || selectedPositions.size > 0 ||
    minPtsNum !== null || maxPtsNum !== null|| search.trim() !== "";

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const min = minPts.trim() !== "" ? parseFloat(minPts) : null;
    const max = maxPts.trim() !== "" ? parseFloat(maxPts) : null;
    return players.filter((p) => {
      if (q && !p.name.toLowerCase().includes(q) && !p.team.toLowerCase().includes(q) && !p.position.toLowerCase().includes(q)) return false;
      if (selectedTeams.size > 0 && !selectedTeams.has(p.team)) return false;
      if (selectedPositions.size > 0 && !selectedPositions.has(p.position)) return false;
      if (min !== null && p.pts < min) return false;
      if (max !== null && p.pts > max) return false;
      return true;
    });
  }, [players, search, selectedTeams, selectedPositions, minPts, maxPts]);

  if (loading) {
    return (
      <div className="players-page">
        <div className="players-loading">Loading players...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="players-page">
        <div className="players-error">
          <span>{error}</span>
          <button
            className="players-retry"
            onClick={() => setRetryKey((k) => k + 1)}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="players-page">
      <div className="players-header">
        <h1>Players</h1>
        <p className="players-subtitle">Players with picks available today</p>
      </div>

      <div className="players-body">
        {/* ── Sidebar ── */}
        <aside className="players-sidebar">
          <div className="sidebar-search-wrap">
            <input
              className="players-search"
              type="text"
              placeholder="Search players…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button className="players-search-clear" onClick={() => setSearch("")}>✕</button>
            )}
          </div>

          <div className="filter-group">
            <div className="filter-group-title">Position</div>
            <div className="filter-chips-grid">
              {allPositions.map((pos) => (
                <label key={pos} className="filter-chip-label">
                  <input
                    type="checkbox"
                    checked={selectedPositions.has(pos)}
                    onChange={() => togglePosition(pos)}
                  />
                  <span className={`filter-chip${selectedPositions.has(pos) ? " filter-chip--active" : ""}`}>
                    {pos}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <div className="filter-group-title">Team</div>
            <div className="filter-chips-grid">
              {allTeams.map((team) => (
                <label key={team} className="filter-chip-label">
                  <input
                    type="checkbox"
                    checked={selectedTeams.has(team)}
                    onChange={() => toggleTeam(team)}
                  />
                  <span className={`filter-chip${selectedTeams.has(team) ? " filter-chip--active" : ""}`}>
                    {team}
                  </span>
                </label>
              ))}
            </div>
          </div>


          <div className="filter-group">
            <div className="filter-group-title">Min PTS</div>
            <input
              className="filter-number-input"
              type="number"
              min="0"
              placeholder="e.g. 5"
              value={minPts}
              onChange={(e) => setMinPts(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <div className="filter-group-title">Max PTS</div>
            <input
              className="filter-number-input"
              type="number"
              min="0"
              placeholder="e.g. 20"
              value={maxPts}
              onChange={(e) => setMaxPts(e.target.value)}
            />
          </div>

          {hasActiveFilters && (
            <button className="filter-clear-btn" onClick={clearFilters}>
              Clear all filters
            </button>
          )}
        </aside>

        <div className="players-table-wrap">
        <table className="players-table">
          <thead>
            <tr>
              <th className="col-photo"></th>
              <th className="col-name">Name</th>
              <th className="col-team">Team</th>
              <th className="col-num">#</th>
              <th className="col-pos">POS</th>
              <th className="col-stat">PTS</th>
              <th className="col-stat">REB</th>
              <th className="col-stat">AST</th>
              <th className="col-logo"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((player) => (
              <tr
                key={player.id}
                className={`player-row${player.has_picks === false ? " player-row--inactive" : ""}`}
                onClick={() => navigate(`/picks/${encodeURIComponent(player.name)}`)}
              >
                <td className="col-photo">
                  <div className="player-headshot-wrap">
                    <img
                      className="player-headshot"
                      src={HEADSHOT_URL(player.id)}
                      alt={player.name}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.visibility =
                          "hidden";
                      }}
                    />
                    {player.has_picks === false && (
                      <span className="player-injured-badge">OUT</span>
                    )}
                  </div>
                </td>
                <td className="col-name">
                  <span className="player-name">{player.name}</span>
                </td>
                <td className="col-team">{player.team}</td>
                <td className="col-num">{player.jersey || "—"}</td>
                <td className="col-pos">{player.position || "—"}</td>
                <td className="col-stat">{fmt(player.pts)}</td>
                <td className="col-stat">{fmt(player.reb)}</td>
                <td className="col-stat">{fmt(player.ast)}</td>
                <td className="col-logo">
                  <TEAM_LOGO abbr={player.team} size={50} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

          {filtered.length === 0 && (
            <div className="players-empty">
              No players match the current filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Players;
