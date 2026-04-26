import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

type Props = {
  disabled: boolean;
  submitted: boolean;
  errorMessage: string | null;
  errorVariant: "warn" | "error" | null;
  shakeKey: number;
  onSubmit: (text: string) => void;
};

export function GuessInput({
  disabled,
  submitted,
  errorMessage,
  errorVariant,
  shakeKey,
  onSubmit,
}: Props) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Clear value when input becomes enabled again (new tick)
  useEffect(() => {
    if (!disabled) {
      setValue("");
      inputRef.current?.focus();
    }
  }, [disabled]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = value.trim();
    if (!v || disabled) return;
    onSubmit(v);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <motion.div
        key={shakeKey}
        animate={shakeKey > 0 ? { x: [0, -8, 8, -5, 5, 0] } : {}}
        transition={{ duration: 0.3 }}
        className="relative w-full"
      >
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={submitted ? "Locked in for this tick" : "Your guess..."}
          aria-label="Enter your guess"
          aria-disabled={disabled}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          className="w-full bg-transparent px-1 py-3 text-text-primary outline-none placeholder:text-text-muted"
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 500,
            fontSize: "1.1rem",
            borderBottom: "2px solid var(--border-active)",
            opacity: disabled ? 0.4 : 1,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        />
      </motion.div>

      <div className="mt-2 h-5">
        <AnimatePresence mode="wait">
          {submitted && !errorMessage && (
            <motion.p
              key="ok"
              initial={{ opacity: 0, y: -2 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="text-primary"
              style={{ fontSize: "0.875rem" }}
            >
              Guess submitted ✓
            </motion.p>
          )}
          {errorMessage && (
            <motion.p
              key={`err-${shakeKey}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{
                fontSize: "0.875rem",
                color: errorVariant === "error" ? "var(--accent-error)" : "var(--accent-warn)",
              }}
            >
              {errorMessage}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </form>
  );
}
