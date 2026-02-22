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
}

const fmt = (v: number) => (v != null && !isNaN(v) ? v.toFixed(1) : "—");

const Players = () => {
  const navigate = useNavigate();
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [retryKey, setRetryKey] = useState(0);

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

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return players;
    return players.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.team.toLowerCase().includes(q) ||
        p.position.toLowerCase().includes(q),
    );
  }, [players, search]);

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
        <p className="players-subtitle">
          Players with picks available today
        </p>

        <div className="players-search-wrap">
          <input
            className="players-search"
            type="text"
            placeholder="Search by name, team, or position…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              className="players-search-clear"
              onClick={() => setSearch("")}
            >
              ✕
            </button>
          )}
        </div>

        <p className="players-count">
          {filtered.length} player{filtered.length !== 1 ? "s" : ""}
          {search ? ` matching "${search}"` : ""}
        </p>
      </div>

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
                className="player-row"
                onClick={() => navigate(`/picks/${encodeURIComponent(player.name)}`)}
              >
                <td className="col-photo">
                  <img
                    className="player-headshot"
                    src={HEADSHOT_URL(player.id)}
                    alt={player.name}
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.visibility =
                        "hidden";
                    }}
                  />
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

        {filtered.length === 0 && search && (
          <div className="players-empty">No players found for "{search}"</div>
        )}
      </div>
    </div>
  );
};

export default Players;
