// Tiny pool of words used by the mock socket. Real backend is plug-and-play.
export const WORD_POOL = [
  "APPLE",
  "PLANET",
  "GUITAR",
  "ROCKET",
  "BRIDGE",
  "JUNGLE",
  "MARKET",
  "WIZARD",
  "FALCON",
  "DRAGON",
  "TIGER",
  "OCEAN",
  "PYTHON",
  "CASTLE",
  "ORANGE",
  "SILVER",
  "GOLDEN",
  "CIPHER",
  "VELVET",
  "MIRROR",
];

export const TICK_DURATION_MS = 5000;
export const TOTAL_ROUNDS = 5;
export const ROUND_END_DELAY_MS = 4000;

export type Scores = { me: number; opponent: number };

export type RevealedState = Array<string | null>;
