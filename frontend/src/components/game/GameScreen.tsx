import { AnimatePresence, motion } from "framer-motion";
import { TopBar } from "./TopBar";
import { WordTiles, type Tile } from "./WordTiles";
import { TimerBar } from "./TimerBar";
import { GuessInput } from "./GuessInput";
import { OpponentIndicator } from "./OpponentIndicator";
import { RoundEndOverlay } from "./RoundEndOverlay";

type Props = {
  myUsername: string;
  opponentUsername: string;
  scores: { me: number; opponent: number };
  roundNumber: number;
  totalRounds: number;
  tiles: Tile[];
  deadline: number | null;
  tickActive: boolean;
  guessSubmitted: boolean;
  errorMessage: string | null;
  errorVariant: "warn" | "error" | null;
  shakeKey: number;
  opponentPulseKey: number;
  opponentGuessedRecently: boolean;
  showRoundEnd: boolean;
  roundResult: {
    winner: "me" | "opponent" | "draw" | null;
    isDraw: boolean;
    revealedWord: string;
  } | null;
  isLastRound: boolean;
  onSubmitGuess: (text: string) => void;
};

export function GameScreen(props: Props) {
  return (
    <motion.div
      key="game"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="relative grid min-h-screen grid-rows-[auto_1fr_auto]"
    >
      <TopBar
        myUsername={props.myUsername}
        opponentUsername={props.opponentUsername}
        scores={props.scores}
        roundNumber={props.roundNumber}
        totalRounds={props.totalRounds}
      />

      <div className="flex items-center justify-center px-4 py-8">
        <WordTiles tiles={props.tiles} />
      </div>

      <div
        className="px-4 py-5 sm:px-6"
        style={{
          backgroundColor: "var(--bg-surface)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        <div className="mx-auto flex max-w-2xl flex-col gap-3">
          <TimerBar deadline={props.deadline} active={props.tickActive} />
          <GuessInput
            disabled={!props.tickActive || props.guessSubmitted}
            submitted={props.guessSubmitted}
            errorMessage={props.errorMessage}
            errorVariant={props.errorVariant}
            shakeKey={props.shakeKey}
            onSubmit={props.onSubmitGuess}
          />
          <div className="flex justify-end">
            <OpponentIndicator
              opponentName={props.opponentUsername}
              pulseKey={props.opponentPulseKey}
              guessedRecently={props.opponentGuessedRecently}
            />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {props.showRoundEnd && props.roundResult && (
          <RoundEndOverlay
            winner={props.roundResult.winner}
            isDraw={props.roundResult.isDraw}
            revealedWord={props.roundResult.revealedWord}
            isLastRound={props.isLastRound}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
