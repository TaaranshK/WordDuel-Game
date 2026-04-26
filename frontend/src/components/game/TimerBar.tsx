import { useEffect, useState } from "react";
import { TICK_DURATION_MS } from "@/game/constants";

type Props = {
  deadline: number | null;
  active: boolean;
};

function colorFor(pct: number): string {
  if (pct > 0.4) return "var(--accent-secondary)";
  if (pct > 0.15) return "var(--accent-warn)";
  return "var(--accent-error)";
}

export function TimerBar({ deadline, active }: Props) {
  const [remaining, setRemaining] = useState<number>(TICK_DURATION_MS);

  useEffect(() => {
    if (!deadline || !active) return;
    let raf: number;
    const tick = () => {
      const r = Math.max(0, deadline - Date.now());
      setRemaining(r);
      if (r > 0) raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [deadline, active]);

  const pct = Math.max(0, Math.min(1, remaining / TICK_DURATION_MS));
  const color = colorFor(pct);
  const seconds = (remaining / 1000).toFixed(1);

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between">
        <span
          className="font-sans uppercase text-text-muted"
          style={{ fontSize: "0.7rem", letterSpacing: "0.12em" }}
        >
          Tick timer
        </span>
        <span
          className="font-display font-semibold tabular-nums transition-colors"
          style={{ fontSize: "1.25rem", color }}
        >
          {seconds}s
        </span>
      </div>
      <div
        className="h-1 w-full overflow-hidden rounded-full"
        style={{ backgroundColor: "var(--bg-elevated)" }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct * 100}%`,
            backgroundColor: color,
            transition: "width 80ms linear, background-color 200ms ease",
          }}
        />
      </div>
    </div>
  );
}
