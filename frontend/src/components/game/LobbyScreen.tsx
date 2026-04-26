import { motion } from "framer-motion";
import { useState } from "react";
import type { DictionaryStats, Player } from "@/api/backend";

type Props = {
  initialUsername: string;
  onFindMatch: (username: string) => void;
  joining?: boolean;
  joinError?: string | null;
  player?: Player | null;
  leaderboard?: Player[] | null;
  dictionaryStats?: DictionaryStats | null;
};

export function LobbyScreen({
  initialUsername,
  onFindMatch,
  joining = false,
  joinError = null,
  player = null,
  leaderboard = null,
  dictionaryStats = null,
}: Props) {
  const [username, setUsername] = useState(initialUsername);
  const [focused, setFocused] = useState(false);
  const trimmed = username.trim();
  const disabled = trimmed.length === 0 || joining;

  return (
    <motion.div
      key="lobby"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="relative flex min-h-screen flex-col items-center justify-center px-6"
      style={{
        background:
          "radial-gradient(ellipse at center, oklch(0.16 0.012 280) 0%, var(--bg-base) 70%)",
      }}
    >
      {/* Subtle dot grid texture */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: "radial-gradient(var(--text-muted) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />

      <div className="relative z-10 flex w-full max-w-[420px] flex-col items-center">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="font-display font-bold leading-none"
          style={{ fontSize: "clamp(3.5rem, 7vw, 5.5rem)", letterSpacing: "-0.04em" }}
        >
          <span className="text-text-primary">WORD</span>
          <span className="text-primary">DUEL</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.08, ease: "easeOut" }}
          className="mt-4 text-center text-text-secondary"
          style={{ fontSize: "1rem", letterSpacing: "0.02em" }}
        >
          Real-time word battle. One word. Two players. No mercy.
        </motion.p>

        <motion.div
          initial={{ opacity: 1, y: 0 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.18, ease: "easeOut" }}
          className="mt-14 w-full"
        >
          <div className="relative w-full">
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value.slice(0, 20))}
              disabled={joining}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !disabled) onFindMatch(trimmed);
              }}
              placeholder="Enter your callsign..."
              aria-label="Your username"
              className="w-full bg-transparent px-1 py-3 text-text-primary outline-none transition-colors placeholder:text-text-muted"
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 500,
                fontSize: "1.1rem",
                borderBottom: `2px solid ${
                  focused ? "var(--accent-primary)" : "var(--border-active)"
                }`,
              }}
            />
            {focused && (
              <span className="absolute right-1 top-1/2 -translate-y-1/2 font-sans text-xs text-text-muted">
                {username.length}/20
              </span>
            )}
          </div>

          <motion.button
            type="button"
            disabled={disabled}
            whileHover={!disabled ? { scale: 1.02 } : undefined}
            whileTap={!disabled ? { scale: 0.98 } : undefined}
            onClick={() => onFindMatch(trimmed)}
            className="mt-8 flex h-[52px] w-full items-center justify-center rounded-full font-display font-semibold transition-all"
            style={{
              backgroundColor: "var(--accent-primary)",
              color: "var(--bg-base)",
              fontSize: "1rem",
              letterSpacing: "0.06em",
              opacity: disabled ? 0.35 : 1,
              boxShadow: !disabled ? "0 0 24px oklch(0.93 0.18 124 / 0.2)" : "none",
            }}
          >
            {joining ? "CONNECTING..." : "FIND MATCH"}
          </motion.button>

          <p className="mt-4 text-center text-text-muted" style={{ fontSize: "0.8rem" }}>
            No account needed. Just a name.
          </p>

          {joinError && (
            <p
              className="mt-4 text-center font-sans"
              style={{ fontSize: "0.85rem", color: "var(--accent-error)" }}
            >
              {joinError}
            </p>
          )}

          {(player || leaderboard || dictionaryStats) && (
            <div
              className="mt-10 w-full rounded-2xl border p-5"
              style={{
                borderColor: "var(--border-subtle)",
                backgroundColor: "oklch(0.17 0.012 280 / 0.6)",
              }}
            >
              <div className="flex items-start justify-between gap-4">
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

              {dictionaryStats && (
                <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-text-muted">
                  <span style={{ fontSize: "0.8rem" }}>
                    Active words: {dictionaryStats.total_active}
                  </span>
                  <span>Â·</span>
                  <span style={{ fontSize: "0.8rem" }}>Easy {dictionaryStats.easy}</span>
                  <span>Â·</span>
                  <span style={{ fontSize: "0.8rem" }}>Medium {dictionaryStats.medium}</span>
                  <span>Â·</span>
                  <span style={{ fontSize: "0.8rem" }}>Hard {dictionaryStats.hard}</span>
                </div>
              )}

              {leaderboard && leaderboard.length > 0 && (
                <div className="mt-5">
                  <p
                    className="font-sans uppercase text-text-muted"
                    style={{ fontSize: "0.65rem", letterSpacing: "0.12em" }}
                  >
                    Top Duelists
                  </p>
                  <div className="mt-3 space-y-2">
                    {leaderboard.slice(0, 5).map((p, idx) => (
                      <div
                        key={p.id}
                        className="flex items-center justify-between rounded-xl px-3 py-2"
                        style={{
                          backgroundColor: "oklch(0.21 0.015 280 / 0.65)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        <span
                          className="font-sans text-text-secondary"
                          style={{ fontSize: "0.85rem" }}
                        >
                          {idx + 1}. {p.username}
                        </span>
                        <span
                          className="font-display font-semibold"
                          style={{ fontSize: "0.9rem", color: "var(--accent-primary)" }}
                        >
                          {p.total_wins}W
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
