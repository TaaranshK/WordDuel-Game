import { AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { TOTAL_ROUNDS } from "@/game/constants";
import { useSocket, useSocketEvent } from "@/game/socket";
import {
  BackendApiError,
  getDictionaryStats,
  getLeaderboard,
  getMatchHistory,
  getPlayerProfile,
  joinPlayer,
  type DictionaryStats,
  type Match,
  type Player,
} from "@/api/backend";
import { LobbyScreen } from "./LobbyScreen";
import { SearchingScreen } from "./SearchingScreen";
import { MatchFoundScreen } from "./MatchFoundScreen";
import { GameScreen } from "./GameScreen";
import { MatchEndScreen } from "./MatchEndScreen";
import type { Tile } from "./WordTiles";

type Phase = "lobby" | "searching" | "matchFound" | "playing" | "matchEnd";

type RoundResult = {
  winner: "me" | "opponent" | "draw" | null;
  isDraw: boolean;
  revealedWord: string;
};

function describeApiError(err: unknown): string {
  if (err instanceof BackendApiError) {
    const body = err.body;
    if (body && typeof body === "object" && !Array.isArray(body)) {
      const message = (body as Record<string, unknown>).message;
      const error = (body as Record<string, unknown>).error;
      if (typeof message === "string") return message;
      if (typeof error === "string") return error;
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}

export function WordDuel() {
  const socket = useSocket();
  const [phase, setPhase] = useState<Phase>("lobby");
  const [username, setUsername] = useState("");

  const [player, setPlayer] = useState<Player | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  const [leaderboard, setLeaderboard] = useState<Player[] | null>(null);
  const [dictionaryStats, setDictionaryStats] = useState<DictionaryStats | null>(null);

  const [matchHistory, setMatchHistory] = useState<Match[] | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [opponentUsername, setOpponentUsername] = useState("");
  const [scores, setScores] = useState({ me: 0, opponent: 0 });
  const [roundNumber, setRoundNumber] = useState(0);

  const [tiles, setTiles] = useState<Tile[]>([]);
  const [deadline, setDeadline] = useState<number | null>(null);
  const [tickActive, setTickActive] = useState(false);
  const [guessSubmitted, setGuessSubmitted] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorVariant, setErrorVariant] = useState<"warn" | "error" | null>(null);
  const [shakeKey, setShakeKey] = useState(0);

  const [opponentPulseKey, setOpponentPulseKey] = useState(0);
  const [opponentGuessedRecently, setOpponentGuessedRecently] = useState(false);
  const opponentRecentTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [showRoundEnd, setShowRoundEnd] = useState(false);
  const [roundResult, setRoundResult] = useState<RoundResult | null>(null);
  const [matchEnd, setMatchEnd] = useState<{
    winner: "me" | "opponent" | "draw";
    finalScores: { me: number; opponent: number };
  } | null>(null);

  // ---- Socket events ----
  useSocketEvent<{
    opponentUsername: string;
    scores: { me: number; opponent: number };
    isAiMatch?: boolean;
  }>("matchFound", (p) => {
    setOpponentUsername(p.opponentUsername);
    setScores(p.scores);
    setRoundNumber(0);
    setMatchEnd(null);
    if (p.isAiMatch) {
      setErrorMessage(`Matched with AI opponent: ${p.opponentUsername}`);
      setErrorVariant("warn");
    }
    setPhase("matchFound");
  });

  useSocketEvent<{ message: string; is_ai_match: boolean }>("aiPairingNotification", (p) => {
    setErrorMessage(p.message);
    setErrorVariant("warn");
    console.log("AI Pairing:", p.message);
  });

  useSocketEvent<{
    roundNumber: number;
    wordLength: number;
    scores: { me: number; opponent: number };
  }>("startRound", (p) => {
    setRoundNumber(p.roundNumber);
    setScores(p.scores);
    setTiles(Array.from({ length: p.wordLength }, () => ({ letter: null, revealed: false })));
    setDeadline(null);
    setTickActive(false);
    setGuessSubmitted(false);
    setErrorMessage(null);
    setErrorVariant(null);
    setShowRoundEnd(false);
    setRoundResult(null);
    setPhase("playing");
  });

  useSocketEvent<{
    tickNumber: number;
    deadline: number;
    revealedState: Array<string | null>;
  }>("tickStart", (p) => {
    setDeadline(p.deadline);
    setTickActive(true);
    setGuessSubmitted(false);
    setErrorMessage(null);
    setErrorVariant(null);
    // Sync tiles from authoritative state
    setTiles((prev) =>
      p.revealedState.map((letter, i) => ({
        letter,
        revealed: letter !== null,
        revealedAt: letter !== null ? prev[i]?.revealedAt : undefined,
      })),
    );
  });

  useSocketEvent<{
    index: number;
    letter: string;
    revealedState: Array<string | null>;
  }>("revealTile", (p) => {
    setTiles((prev) => {
      const next = [...prev];
      next[p.index] = { letter: p.letter, revealed: true, revealedAt: Date.now() };
      return next;
    });
  });

  useSocketEvent<{ tickNumber: number }>("opponentGuessed", () => {
    setOpponentPulseKey((k) => k + 1);
    setOpponentGuessedRecently(true);
    if (opponentRecentTimer.current) clearTimeout(opponentRecentTimer.current);
    opponentRecentTimer.current = setTimeout(() => setOpponentGuessedRecently(false), 2000);
  });

  useSocketEvent<{
    winner: "me" | "opponent" | "draw" | null;
    revealedWord: string;
    scores: { me: number; opponent: number };
    isDraw: boolean;
  }>("roundEnd", (p) => {
    setTickActive(false);
    setDeadline(null);
    setScores(p.scores);
    // Reveal full word with stagger
    setTiles(
      p.revealedWord.split("").map((letter, i) => ({
        letter,
        revealed: true,
        revealedAt: Date.now() + i * 60,
      })),
    );
    setRoundResult({
      winner: p.winner,
      isDraw: p.isDraw,
      revealedWord: p.revealedWord,
    });
    setShowRoundEnd(true);
  });

  useSocketEvent<{
    winner: "me" | "opponent" | "draw";
    finalScores: { me: number; opponent: number };
  }>("matchEnd", (p) => {
    setMatchEnd({ winner: p.winner, finalScores: p.finalScores });
    setShowRoundEnd(false);
    setPhase("matchEnd");
    if (player) {
      void refreshLobbyData();
      void refreshMatchHistory(player.id);
      void getPlayerProfile(player.id)
        .then((p2) => setPlayer(p2))
        .catch(() => {
          // ignore
        });
    }
  });

  useSocketEvent<{ code: string; message: string }>("error", (p) => {
    if (p.code === "INVALID_GUESS") {
      setShakeKey((k) => k + 1);
      setErrorMessage("Invalid guess");
      setErrorVariant("error");
    } else if (p.code === "ALREADY_GUESSED") {
      setErrorMessage("Already submitted this tick");
      setErrorVariant("warn");
    } else if (p.code === "LATE_SUBMISSION") {
      setErrorMessage("Too slow — tick ended");
      setErrorVariant("error");
    } else {
      setErrorMessage(p.message);
      setErrorVariant("error");
    }
  });

  const refreshLobbyData = useCallback(async () => {
    try {
      setLeaderboard(await getLeaderboard());
    } catch {
      // ignore
    }

    try {
      setDictionaryStats(await getDictionaryStats());
    } catch {
      // ignore
    }
  }, []);

  const refreshMatchHistory = useCallback(async (playerId: number) => {
    setHistoryError(null);
    setHistoryLoading(true);
    try {
      setMatchHistory(await getMatchHistory(playerId));
    } catch (err) {
      setMatchHistory([]);
      setHistoryError(describeApiError(err));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshLobbyData();
  }, [refreshLobbyData]);

  // ---- Actions ----
  const handleFindMatch = useCallback(
    async (name: string) => {
      if (joining) return;
      const cleaned = name.trim();
      if (!cleaned) return;

      setJoinError(null);
      setJoining(true);
      try {
        const resp = await joinPlayer(cleaned);
        setPlayer(resp.player);
        setSessionToken(resp.session_token);
        setUsername(resp.player.username);

        setPhase("searching");
        socket.send("joinLobby", { username: resp.player.username });

        void refreshLobbyData();
        void refreshMatchHistory(resp.player.id);
      } catch (err) {
        setJoinError(describeApiError(err));
      } finally {
        setJoining(false);
      }
    },
    [joining, refreshLobbyData, refreshMatchHistory, socket],
  );

  const handleCancelSearch = useCallback(() => {
    socket.send("leaveMatch", {});
    setPhase("lobby");
  }, [socket]);

  const handleSubmitGuess = useCallback(
    (text: string) => {
      setGuessSubmitted(true);
      socket.send("submitGuess", {
        guessText: text,
        clientSentAt: Date.now(),
      });
    },
    [socket],
  );

  const handlePlayAgain = useCallback(() => {
    setMatchEnd(null);
    setScores({ me: 0, opponent: 0 });
    setPhase("searching");
    socket.send("joinLobby", { username });
  }, [socket, username]);

  const handleQuit = useCallback(() => {
    socket.send("leaveMatch", {});
    setMatchEnd(null);
    setScores({ me: 0, opponent: 0 });
    setPhase("lobby");
  }, [socket]);

  // Cleanup
  useEffect(
    () => () => {
      if (opponentRecentTimer.current) clearTimeout(opponentRecentTimer.current);
    },
    [],
  );

  const isLastRound = roundNumber >= TOTAL_ROUNDS;

  return (
    <AnimatePresence mode="wait">
      {phase === "lobby" && (
        <LobbyScreen
          key="lobby"
          initialUsername={username}
          onFindMatch={handleFindMatch}
          joining={joining}
          joinError={joinError}
          player={player}
          leaderboard={leaderboard}
          dictionaryStats={dictionaryStats}
        />
      )}
      {phase === "searching" && <SearchingScreen key="searching" onCancel={handleCancelSearch} />}
      {phase === "matchFound" && (
        <MatchFoundScreen
          key="matchFound"
          myUsername={username}
          opponentUsername={opponentUsername}
          totalRounds={TOTAL_ROUNDS}
        />
      )}
      {phase === "playing" && (
        <GameScreen
          key="playing"
          myUsername={username}
          opponentUsername={opponentUsername}
          scores={scores}
          roundNumber={roundNumber}
          totalRounds={TOTAL_ROUNDS}
          tiles={tiles}
          deadline={deadline}
          tickActive={tickActive}
          guessSubmitted={guessSubmitted}
          errorMessage={errorMessage}
          errorVariant={errorVariant}
          shakeKey={shakeKey}
          opponentPulseKey={opponentPulseKey}
          opponentGuessedRecently={opponentGuessedRecently}
          showRoundEnd={showRoundEnd}
          roundResult={roundResult}
          isLastRound={isLastRound}
          onSubmitGuess={handleSubmitGuess}
        />
      )}
      {phase === "matchEnd" && matchEnd && (
        <MatchEndScreen
          key="matchEnd"
          myUsername={username}
          opponentUsername={opponentUsername}
          finalScores={matchEnd.finalScores}
          totalRounds={TOTAL_ROUNDS}
          winner={matchEnd.winner}
          player={player}
          sessionToken={sessionToken}
          matchHistory={matchHistory}
          historyLoading={historyLoading}
          historyError={historyError}
          onPlayAgain={handlePlayAgain}
          onQuit={handleQuit}
        />
      )}
    </AnimatePresence>
  );
}
