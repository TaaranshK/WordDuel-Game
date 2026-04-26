import { motion } from "framer-motion";

type Tile = { letter: string | null; revealed: boolean; revealedAt?: number };

type Props = {
  tiles: Tile[];
};

export function WordTiles({ tiles }: Props) {
  const count = tiles.length;
  // Shrink tiles & gap when many letters
  const sizeClass =
    count > 8
      ? "w-[clamp(40px,7vw,60px)] h-[clamp(40px,7vw,60px)] text-[clamp(1.2rem,2.8vw,2rem)]"
      : "w-[clamp(52px,8vw,80px)] h-[clamp(52px,8vw,80px)] text-[clamp(1.6rem,3.5vw,2.8rem)]";
  const gapClass = count > 8 ? "gap-2 sm:gap-3" : "gap-2 sm:gap-4";

  return (
    <div className={`flex flex-wrap justify-center items-center ${gapClass}`}>
      {tiles.map((tile, i) => {
        const isRevealed = tile.revealed && tile.letter;
        return (
          <div
            key={i}
            className={`relative flex items-center justify-center rounded-[10px] font-display font-bold transition-colors ${sizeClass} ${
              isRevealed ? "animate-tile-reveal" : ""
            }`}
            style={{
              backgroundColor: isRevealed ? "var(--tile-revealed-bg)" : "var(--tile-hidden)",
              border: isRevealed
                ? "1.5px solid transparent"
                : "1.5px solid var(--tile-border-hidden)",
              color: isRevealed ? "var(--tile-revealed-text)" : "var(--text-muted)",
              animationDelay: isRevealed ? `${i * 30}ms` : undefined,
            }}
          >
            {isRevealed ? tile.letter : "_"}
          </div>
        );
      })}
    </div>
  );
}

export type { Tile };
