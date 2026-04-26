import { motion, AnimatePresence } from "framer-motion";

type Props = {
  opponentName: string;
  pulseKey: number; // increments on each opponentGuessed
  guessedRecently: boolean;
};

export function OpponentIndicator({ opponentName, pulseKey, guessedRecently }: Props) {
  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-2.5 w-2.5">
        <AnimatePresence>
          {pulseKey > 0 && (
            <motion.span
              key={pulseKey}
              initial={{ scale: 1, opacity: 0.7 }}
              animate={{ scale: 3, opacity: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="absolute inset-0 rounded-full"
              style={{ backgroundColor: "var(--accent-secondary)" }}
            />
          )}
        </AnimatePresence>
        <motion.span
          key={`dot-${pulseKey}`}
          animate={pulseKey > 0 ? { scale: [1, 2.2, 1] } : {}}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="relative inline-flex h-2.5 w-2.5 rounded-full"
          style={{
            backgroundColor: guessedRecently ? "var(--accent-secondary)" : "var(--text-muted)",
          }}
        />
      </span>
      <span className="font-sans text-text-muted" style={{ fontSize: "0.8rem" }}>
        <span className="text-text-secondary">{opponentName}</span>{" "}
        {guessedRecently ? "guessed!" : "thinking..."}
      </span>
    </div>
  );
}
