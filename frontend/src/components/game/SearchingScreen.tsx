import { motion } from "framer-motion";

type Props = {
  onCancel: () => void;
};

export function SearchingScreen({ onCancel }: Props) {
  return (
    <motion.div
      key="searching"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="flex min-h-screen flex-col items-center justify-center px-6"
    >
      <div className="relative mb-12 flex h-32 w-32 items-center justify-center">
        {/* Two pulsing rings */}
        {[0, 0.7].map((delay) => (
          <span
            key={delay}
            className="absolute inset-0 rounded-full border"
            style={{
              borderColor: "var(--accent-primary)",
              animation: `ringPulse 2s ease-out ${delay}s infinite`,
            }}
          />
        ))}
        <span
          className="block h-3 w-3 rounded-full"
          style={{ backgroundColor: "var(--accent-primary)" }}
        />
      </div>

      <h2 className="font-display font-semibold text-text-primary" style={{ fontSize: "2rem" }}>
        Finding opponent
        <span className="ml-1 inline-flex">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              style={{
                animation: `ellipsisDot 1.4s ease-in-out ${i * 0.4}s infinite`,
              }}
            >
              .
            </span>
          ))}
        </span>
      </h2>

      <p className="mt-3 text-text-secondary" style={{ fontSize: "0.95rem" }}>
        Matching you with a worthy duelist
      </p>

      <button
        type="button"
        onClick={onCancel}
        className="mt-12 text-text-secondary underline-offset-4 transition-colors hover:text-text-primary hover:underline"
        style={{ fontSize: "0.875rem" }}
      >
        Cancel search
      </button>
    </motion.div>
  );
}
