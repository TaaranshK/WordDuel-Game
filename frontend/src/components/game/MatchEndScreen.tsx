import { motion } from "framer-motion";
import type { Match, Player } from "@/api/backend";

type Props = {
  myUsername: string;
  opponentUsername: string;
  finalScores: { me: number; opponent: number };
  totalRounds: number;
  winner: "me" | "opponent" | "draw";
  player?: Player | null;
  sessionToken?: string | null;
  matchHistory?: Match[] | null;
  historyLoading?: boolean;
  historyError?: string | null;
  onPlayAgain: () => void;
  onQuit: () => void;
};

const OUTCOMES = {
  me: { text: "VICTORY", color: "var(--accent-primary)" },
  opponent: { text: "DEFEATED", color: "var(--accent-error)" },
  draw: { text: "STALEMATE", color: "var(--accent-warn)" },
};

export function MatchEndScreen({
  myUsername,
  opponentUsername,
  finalScores,
  totalRounds,
  winner,
  player = null,
  sessionToken = null,
  matchHistory = null,
  historyLoading = false,
  historyError = null,
  onPlayAgain,
  onQuit,
}: Props) {
  const outcome = OUTCOMES[winner];

  const historyRows =
    matchHistory?.slice(0, 5).map((m) => {
      const isP1 = player?.id === m.player1.id;
      const opponent = isP1 ? m.player2.username : m.player1.username;
      const myScore = isP1 ? m.score1 : m.score2;
      const oppScore = isP1 ? m.score2 : m.score1;

      let result: "win" | "loss" | "draw" | "unknown" = "unknown";
      if (m.winner == null) result = "draw";
      else if (player && m.winner.id === player.id) result = "win";
      else if (player) result = "loss";

      return { matchId: m.id, opponent, myScore, oppScore, result };
    }) ?? [];

  return (
    <motion.div
      key="matchEnd"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="flex min-h-screen flex-col items-center justify-center px-6"
    >
      <motion.h1
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display font-bold text-center"
        style={{
          fontSize: "clamp(3.5rem, 8vw, 6rem)",
          color: outcome.color,
          letterSpacing: "-0.04em",
          lineHeight: 0.95,
        }}
      >
        {outcome.text}
      </motion.h1>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-12 flex items-center gap-6 sm:gap-10"
      >
        <div className="text-center">
          <div
            className="font-display font-bold text-text-primary"
            style={{ fontSize: "clamp(2.5rem, 6vw, 3.5rem)", lineHeight: 1 }}
          >
            {finalScores.me}
          </div>
          <div
            className="mt-2 font-sans text-text-secondary truncate max-w-[120px] sm:max-w-[180px]"
            style={{ fontSize: "0.9rem" }}
          >
            {myUsername}
          </div>
        </div>

        <div className="font-display font-bold text-text-muted" style={{ fontSize: "2rem" }}>
          —
        </div>

        <div className="text-center">
          <div
            className="font-display font-bold text-text-primary"
            style={{ fontSize: "clamp(2.5rem, 6vw, 3.5rem)", lineHeight: 1 }}
          >
            {finalScores.opponent}
          </div>
          <div
            className="mt-2 font-sans text-text-secondary truncate max-w-[120px] sm:max-w-[180px]"
            style={{ fontSize: "0.9rem" }}
          >
            {opponentUsername}
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-8 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-text-muted"
        style={{ fontSize: "0.85rem" }}
      >
        <span>Rounds Played: {totalRounds}</span>
        <span>·</span>
        <span>Your Wins: {finalScores.me}</span>
        <span>·</span>
        <span>Opponent Wins: {finalScores.opponent}</span>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="mt-12 flex flex-col gap-3 sm:flex-row"
      >
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onPlayAgain}
          className="flex h-[52px] min-w-[180px] items-center justify-center rounded-full font-display font-semibold"
          style={{
            backgroundColor: "var(--accent-primary)",
            color: "var(--bg-base)",
            fontSize: "1rem",
            letterSpacing: "0.06em",
            boxShadow: "0 0 24px oklch(0.93 0.18 124 / 0.25)",
          }}
        >
          PLAY AGAIN
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onQuit}
          className="flex h-[52px] min-w-[180px] items-center justify-center rounded-full font-display font-semibold transition-colors hover:text-text-primary"
          style={{
            backgroundColor: "transparent",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-active)",
            fontSize: "1rem",
            letterSpacing: "0.06em",
          }}
        >
          QUIT
        </motion.button>
      </motion.div>

      {(player || sessionToken || matchHistory || historyLoading || historyError) && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="mt-10 w-full max-w-2xl rounded-2xl border p-5"
          style={{
            borderColor: "var(--border-subtle)",
            backgroundColor: "oklch(0.17 0.012 280 / 0.6)",
          }}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p
                className="font-sans uppercase text-text-muted"
                style={{ fontSize: "0.65rem", letterSpacing: "0.12em" }}
              >
                Backend APIs (REST)
              </p>
              <p className="mt-1 text-text-secondary" style={{ fontSize: "0.85rem" }}>
                {player
                  ? `Player #${player.id} · ${player.total_wins} wins · ${player.total_matches} matches`
                  : "Join to load player stats."}
              </p>
            </div>

            <span
              className="rounded-full px-3 py-1 font-sans text-xs"
              style={{
                backgroundColor: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-secondary)",
              }}
            >
              /api/*
            </span>
          </div>

          {historyLoading && (
            <p className="mt-4 font-sans text-text-muted" style={{ fontSize: "0.85rem" }}>
              Loading match historyâ€¦
            </p>
          )}

          {historyError && (
            <p
              className="mt-4 font-sans"
              style={{ fontSize: "0.85rem", color: "var(--accent-error)" }}
            >
              {historyError}
            </p>
          )}

          {historyRows.length > 0 && (
            <div className="mt-5">
              <p
                className="font-sans uppercase text-text-muted"
                style={{ fontSize: "0.65rem", letterSpacing: "0.12em" }}
              >
                Recent Matches
              </p>
              <div className="mt-3 space-y-2">
                {historyRows.map((r) => (
                  <div
                    key={r.matchId}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl px-3 py-2"
                    style={{
                      backgroundColor: "oklch(0.21 0.015 280 / 0.65)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <span className="font-sans text-text-secondary" style={{ fontSize: "0.85rem" }}>
                      #{r.matchId} vs {r.opponent}
                    </span>
                    <span
                      className="font-display font-semibold"
                      style={{
                        fontSize: "0.9rem",
                        color:
                          r.result === "win"
                            ? "var(--accent-primary)"
                            : r.result === "loss"
                              ? "var(--accent-error)"
                              : "var(--accent-warn)",
                      }}
                    >
                      {r.myScore}â€“{r.oppScore} {r.result.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
