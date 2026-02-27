import React, { useState, useEffect } from "react";
import "./Games.css";

import * as NBA_LOGOS from "../components/nbaLogos";

const TEAM_LOGO = ({ abbr, size }: { abbr: string; size: number }) => {
  const Logo = (
    NBA_LOGOS as Record<string, React.ComponentType<{ size: number }>>
  )[abbr];
  if (!Logo) return null;
  return <Logo size={size} />;
};

const TEAM_INFO: Record<string, { name: string; city: string }> = {
  ATL: { name: "Hawks", city: "Atlanta" },
  BOS: { name: "Celtics", city: "Boston" },
  BKN: { name: "Nets", city: "Brooklyn" },
  CHA: { name: "Hornets", city: "Charlotte" },
  CHI: { name: "Bulls", city: "Chicago" },
  CLE: { name: "Cavaliers", city: "Cleveland" },
  DAL: { name: "Mavericks", city: "Dallas" },
  DEN: { name: "Nuggets", city: "Denver" },
  DET: { name: "Pistons", city: "Detroit" },
  GSW: { name: "Warriors", city: "Golden State" },
  HOU: { name: "Rockets", city: "Houston" },
  IND: { name: "Pacers", city: "Indiana" },
  LAC: { name: "Clippers", city: "LA" },
  LAL: { name: "Lakers", city: "LA" },
  MEM: { name: "Grizzlies", city: "Memphis" },
  MIA: { name: "Heat", city: "Miami" },
  MIL: { name: "Bucks", city: "Milwaukee" },
  MIN: { name: "Timberwolves", city: "Minnesota" },
  NOP: { name: "Pelicans", city: "New Orleans" },
  NYK: { name: "Knicks", city: "New York" },
  OKC: { name: "Thunder", city: "Oklahoma City" },
  ORL: { name: "Magic", city: "Orlando" },
  PHI: { name: "Sixers", city: "Philadelphia" },
  PHX: { name: "Suns", city: "Phoenix" },
  POR: { name: "Trail Blazers", city: "Portland" },
  SAC: { name: "Kings", city: "Sacramento" },
  SAS: { name: "Spurs", city: "San Antonio" },
  TOR: { name: "Raptors", city: "Toronto" },
  UTA: { name: "Jazz", city: "Utah" },
  WAS: { name: "Wizards", city: "Washington" },
};

interface Game {
  GAMECODE: string;
  GAME_STATUS_TEXT: string;
  GAME_STATUS_ID: number;
  ARENA_NAME: string;
}

function parseTeams(gamecode: string) {
  const matchup = gamecode.split("/")[1] || "";
  const away = matchup.slice(0, 3);
  const home = matchup.slice(3);
  return {
    away,
    home,
    awayFull: TEAM_INFO[away]
      ? `${TEAM_INFO[away].city} ${TEAM_INFO[away].name}`
      : away,
    homeFull: TEAM_INFO[home]
      ? `${TEAM_INFO[home].city} ${TEAM_INFO[home].name}`
      : home,
  };
}

const Games = () => {
  const [games, setGames] = useState<Game[]>([]);
  const [gameDate, setGameDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/api/games/today`);
        const data = await res.json();
        if (data.success) {
          setGames(data.games);
          setGameDate(data.date);
        } else {
          setError(data.error || "Failed to fetch games");
        }
      } catch {
        setError("Could not connect to the server");
      } finally {
        setLoading(false);
      }
    };
    fetchGames();
  }, []);

  const formatDate = (dateStr: string) => {
    const [year, month, day] = dateStr.split("-").map(Number);
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  const tickerText = games.map((g) => {
    const { away, home } = parseTeams(g.GAMECODE);
    const time = g.GAME_STATUS_TEXT?.trim() || "TBD";
    return `${away} vs ${home} @ ${time}`;
  })
  .join("  |  ");
  
  const tickerAria = `Today's games: ${tickerText}`;

  if (loading) {
    return (
      <div className="games-page">
        <div className="games-loading">Loading games...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="games-page">
        <div className="games-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="games-page">
      <div className="games-ticker" role="region" aria-label={tickerAria}>
        <div className="games-ticker-track">
          <div className="games-ticker-content">
            <span>{tickerText}</span>
            <span aria-hidden="true">{tickerText}</span>
          </div>
        </div>
      </div>
      <div className="games-header">
        <h1>Games</h1>
        {gameDate && <p className="games-date">{formatDate(gameDate)}</p>}
        <p className="games-count">
          {games.length} game{games.length !== 1 ? "s" : ""} scheduled
        </p>
      </div>

      <div className="games-grid">
        {games.map((game) => {
          const { away, home, awayFull, homeFull } = parseTeams(game.GAMECODE);
          return (
            <div key={game.GAMECODE} className="game-card">
              <div className="game-status">{game.GAME_STATUS_TEXT}</div>
              <div className="game-matchup">
                <div className="game-team">
                  <TEAM_LOGO abbr={away} size={80} />
                  <span className="team-abbr">{away}</span>
                  <span className="team-name">{awayFull}</span>
                </div>
                <span className="game-at">@</span>
                <div className="game-team">
                  <TEAM_LOGO abbr={home} size={80} />
                  <span className="team-abbr">{home}</span>
                  <span className="team-name">{homeFull}</span>
                </div>
              </div>
              <div className="game-arena">{game.ARENA_NAME}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Games;
