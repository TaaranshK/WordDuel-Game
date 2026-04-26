import { motion } from "framer-motion";
import { useEffect, useState } from "react";

type Props = {
  myUsername: string;
  opponentUsername: string;
  scores: { me: number; opponent: number };
  roundNumber: number;
  totalRounds: number;
};

function ScoreBadge({ value, flash }: { value: number; flash: "win" | "lose" | null }) {
  return (
    <motion.div
      key={`${value}-${flash}`}
      animate={flash ? { scale: [1, 1.25, 1] } : { scale: 1 }}
      transition={{ duration: 0.4 }}
      className="flex h-10 min-w-[40px] items-center justify-center rounded-full px-3"
      style={{
        backgroundColor: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        color:
          flash === "win"
            ? "var(--accent-primary)"
            : flash === "lose"
              ? "var(--accent-error)"
              : "var(--text-primary)",
        fontFamily: "var(--font-display)",
        fontWeight: 600,
        fontSize: "1.4rem",
      }}
    >
      {value}
    </motion.div>
  );
}

function useScoreFlash(
  value: number,
  side: "me" | "opponent",
  myDelta: number,
  opponentDelta: number,
) {
  const [flash, setFlash] = useState<"win" | "lose" | null>(null);
  useEffect(() => {
    const delta = side === "me" ? myDelta : opponentDelta;
    if (delta > 0) {
      // For "me" gaining a point → win flash; for opponent gaining → lose flash for me side display
      setFlash(side === "me" ? "win" : "lose");
      const t = setTimeout(() => setFlash(null), 700);
      return () => clearTimeout(t);
    }
  }, [value, side, myDelta, opponentDelta]);
  return flash;
}

function truncateName(name: string, max = 14) {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function TopBar({ myUsername, opponentUsername, scores, roundNumber, totalRounds }: Props) {
  const [prev, setPrev] = useState(scores);
  const myDelta = scores.me - prev.me;
  const opDelta = scores.opponent - prev.opponent;
  const meFlash = useScoreFlash(scores.me, "me", myDelta, opDelta);
  const opFlash = useScoreFlash(scores.opponent, "opponent", myDelta, opDelta);

  useEffect(() => {
    const t = setTimeout(() => setPrev(scores), 800);
    return () => clearTimeout(t);
  }, [scores]);

  return (
    <div
      className="flex h-[72px] items-center justify-between px-4 sm:px-6"
      style={{
        backgroundColor: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex items-center gap-3">
        <ScoreBadge value={scores.me} flash={meFlash} />
        <div className="hidden flex-col sm:flex">
          <span
            className="font-sans uppercase text-text-muted"
            style={{ fontSize: "0.65rem", letterSpacing: "0.12em" }}
          >
            You
          </span>
          <span
            className="font-display font-semibold text-text-primary"
            style={{ fontSize: "1rem" }}
          >
            {truncateName(myUsername, 12)}
          </span>
        </div>
      </div>

      <div
        className="font-sans uppercase text-text-muted"
        style={{ fontSize: "0.7rem", letterSpacing: "0.14em" }}
      >
        Round {roundNumber} / {totalRounds}
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden flex-col items-end sm:flex">
          <span
            className="font-sans uppercase text-text-muted"
            style={{ fontSize: "0.65rem", letterSpacing: "0.12em" }}
          >
            Opponent
          </span>
          <span
            className="font-display font-semibold text-text-primary"
            style={{ fontSize: "1rem" }}
          >
            {truncateName(opponentUsername, 12)}
          </span>
        </div>
        <ScoreBadge value={scores.opponent} flash={opFlash} />
      </div>
    </div>
  );
}
