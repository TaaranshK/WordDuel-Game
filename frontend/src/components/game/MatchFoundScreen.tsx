import { motion } from "framer-motion";
import { useEffect, useState } from "react";

type Props = {
  myUsername: string;
  opponentUsername: string;
  totalRounds: number;
};

export function MatchFoundScreen({ myUsername, opponentUsername, totalRounds }: Props) {
  const [count, setCount] = useState(3);

  useEffect(() => {
    if (count <= 0) return;
    const t = setTimeout(() => setCount((c) => c - 1), 800);
    return () => clearTimeout(t);
  }, [count]);

  return (
    <motion.div
      key="matchFound"
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="flex min-h-screen flex-col items-center justify-center px-6"
      style={{
        background: "radial-gradient(ellipse at center, var(--bg-surface) 0%, var(--bg-base) 80%)",
      }}
    >
      <div className="flex w-full max-w-4xl items-center justify-center gap-6 sm:gap-12">
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex-1 text-right"
        >
          <div
            className="mb-2 font-sans uppercase text-text-muted"
            style={{ fontSize: "0.7rem", letterSpacing: "0.12em" }}
          >
            You
          </div>
          <div
            className="font-display font-bold text-text-primary truncate"
            style={{ fontSize: "clamp(1.4rem, 4vw, 2.3rem)" }}
          >
            {myUsername}
          </div>
        </motion.div>

        <motion.div
          initial={{ scale: 1.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
          className="font-display font-bold text-primary"
          style={{ fontSize: "clamp(2rem, 6vw, 3.8rem)" }}
        >
          VS
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex-1 text-left"
        >
          <div
            className="mb-2 font-sans uppercase text-text-muted"
            style={{ fontSize: "0.7rem", letterSpacing: "0.12em" }}
          >
            Opponent
          </div>
          <div
            className="font-display font-bold text-text-primary truncate"
            style={{ fontSize: "clamp(1.4rem, 4vw, 2.3rem)" }}
          >
            {opponentUsername}
          </div>
        </motion.div>
      </div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="mt-8 text-text-secondary"
        style={{ fontSize: "0.875rem" }}
      >
        Best of {totalRounds} rounds · 5 seconds per tick
      </motion.p>

      <div className="mt-12 flex flex-col items-center">
        <p className="mb-3 text-text-muted" style={{ fontSize: "0.8rem", letterSpacing: "0.1em" }}>
          ROUND 1 STARTS IN
        </p>
        <motion.div
          key={count}
          initial={{ scale: 1.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3, ease: [0.34, 1.56, 0.64, 1] }}
          className="font-display font-bold text-primary"
          style={{ fontSize: "5rem", lineHeight: 1 }}
        >
          {count > 0 ? count : "GO"}
        </motion.div>
      </div>
    </motion.div>
  );
}
