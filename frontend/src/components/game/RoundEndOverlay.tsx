import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { ROUND_END_DELAY_MS } from "@/game/constants";

type Props = {
  winner: "me" | "opponent" | "draw" | null;
  isDraw: boolean;
  revealedWord: string;
  isLastRound: boolean;
};

const HEADLINES: Record<string, { text: string; color: string }> = {
  me: { text: "YOU GOT IT!", color: "var(--accent-primary)" },
  opponent: { text: "OPPONENT WINS", color: "var(--accent-error)" },
  draw: { text: "DRAW!", color: "var(--accent-warn)" },
  none: { text: "NO WINNER", color: "var(--text-secondary)" },
};

export function RoundEndOverlay({ winner, isDraw, revealedWord, isLastRound }: Props) {
  const key = isDraw ? "draw" : (winner ?? "none");
  const headline = HEADLINES[key];
  const [secondsLeft, setSecondsLeft] = useState(Math.ceil(ROUND_END_DELAY_MS / 1000));

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => {
      const elapsed = Date.now() - start;
      setSecondsLeft(Math.max(0, Math.ceil((ROUND_END_DELAY_MS - elapsed) / 1000)));
    }, 200);
    return () => clearInterval(id);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="absolute inset-0 z-20 flex flex-col items-center justify-center px-6"
      style={{
        backgroundColor: "oklch(0.13 0.01 280 / 0.85)",
        backdropFilter: "blur(8px)",
      }}
    >
      <motion.h2
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display font-bold text-center"
        style={{
          fontSize: "clamp(2rem, 5vw, 3.5rem)",
          color: headline.color,
          letterSpacing: "-0.02em",
        }}
      >
        {headline.text}
      </motion.h2>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-6 text-center"
      >
        <p
          className="font-sans text-text-secondary"
          style={{ fontSize: "0.85rem", letterSpacing: "0.08em", textTransform: "uppercase" }}
        >
          The word was
        </p>
        <p
          className="mt-2 font-display font-semibold text-text-primary"
          style={{ fontSize: "clamp(1.6rem, 4vw, 2.4rem)", letterSpacing: "0.08em" }}
        >
          {revealedWord}
        </p>
      </motion.div>

      <AnimatePresence>
        {!isLastRound && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-12 flex items-center gap-3 rounded-full px-4 py-2"
            style={{
              backgroundColor: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <span className="font-sans text-text-secondary" style={{ fontSize: "0.8rem" }}>
              Next round in {secondsLeft}s
            </span>
            <div
              className="h-1 w-20 overflow-hidden rounded-full"
              style={{ backgroundColor: "var(--bg-surface)" }}
            >
              <motion.div
                initial={{ width: "100%" }}
                animate={{ width: "0%" }}
                transition={{ duration: ROUND_END_DELAY_MS / 1000, ease: "linear" }}
                className="h-full"
                style={{ backgroundColor: "var(--accent-primary)" }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
