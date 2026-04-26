import {
  ROUND_END_DELAY_MS,
  TICK_DURATION_MS,
  TOTAL_ROUNDS,
  WORD_POOL,
  type RevealedState,
  type Scores,
} from "./constants";

/**
 * MockSocket — a self-contained event emitter that simulates a backend
 * matchmaker, opponent, and tick scheduler. Same event names as the real
 * Socket.IO contract so swapping in the real socket is a one-liner.
 */

type Listener = (...args: unknown[]) => void;

type OpponentProfile = {
  name: string;
  // Probability the bot guesses correctly on any given tick once
  // it has at least `minRevealed` letters revealed.
  guessAccuracy: number;
  minRevealed: number;
  // Probability the bot "submits" a guess at all this tick (animation only)
  guessChance: number;
};

const OPPONENTS: OpponentProfile[] = [
  { name: "NebulaFox", guessAccuracy: 0.45, minRevealed: 2, guessChance: 0.55 },
  { name: "SilentDuel", guessAccuracy: 0.35, minRevealed: 3, guessChance: 0.7 },
  { name: "QuickByte", guessAccuracy: 0.55, minRevealed: 2, guessChance: 0.6 },
  { name: "Vortex_07", guessAccuracy: 0.4, minRevealed: 3, guessChance: 0.65 },
  { name: "PixelHawk", guessAccuracy: 0.5, minRevealed: 2, guessChance: 0.5 },
];

const pick = <T>(arr: T[]) => arr[Math.floor(Math.random() * arr.length)];

export class MockSocket {
  private listeners = new Map<string, Set<Listener>>();
  private matchId: string | null = null;
  private opponent: OpponentProfile | null = null;
  private scores: Scores = { me: 0, opponent: 0 };
  private roundNumber = 0;
  private currentWord = "";
  private revealedState: RevealedState = [];
  private revealOrder: number[] = [];
  private tickNumber = 0;
  private tickTimer: ReturnType<typeof setTimeout> | null = null;
  private opponentTimer: ReturnType<typeof setTimeout> | null = null;
  private myGuessThisTick = false;
  private opponentGuessThisTick: { correct: boolean } | null = null;
  private roundId: string | null = null;
  private destroyed = false;

  on(event: string, cb: Listener) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(cb);
  }

  off(event: string, cb: Listener) {
    this.listeners.get(event)?.delete(cb);
  }

  private emit(event: string, payload?: unknown) {
    if (this.destroyed) return;
    this.listeners.get(event)?.forEach((cb) => cb(payload));
  }

  /** Mimic socket.emit (client → server) */
  send(event: string, payload?: Record<string, unknown>) {
    if (this.destroyed) return;
    switch (event) {
      case "joinLobby":
        this.handleJoinLobby();
        break;
      case "submitGuess":
        this.handleSubmitGuess(payload?.guessText as string);
        break;
      case "leaveMatch":
        this.reset();
        break;
    }
  }

  destroy() {
    this.destroyed = true;
    if (this.tickTimer) clearTimeout(this.tickTimer);
    if (this.opponentTimer) clearTimeout(this.opponentTimer);
    this.listeners.clear();
  }

  private reset() {
    if (this.tickTimer) clearTimeout(this.tickTimer);
    if (this.opponentTimer) clearTimeout(this.opponentTimer);
    this.tickTimer = null;
    this.opponentTimer = null;
    this.matchId = null;
    this.opponent = null;
    this.scores = { me: 0, opponent: 0 };
    this.roundNumber = 0;
    this.currentWord = "";
    this.revealedState = [];
    this.revealOrder = [];
    this.tickNumber = 0;
    this.myGuessThisTick = false;
    this.opponentGuessThisTick = null;
    this.roundId = null;
  }

  private handleJoinLobby() {
    this.reset();
    // Simulate matchmaking delay (1.2s – 2.4s)
    const delay = 1200 + Math.random() * 1200;
    setTimeout(() => {
      if (this.destroyed) return;
      this.opponent = pick(OPPONENTS);
      this.matchId = `m_${Math.random().toString(36).slice(2, 9)}`;
      this.emit("matchFound", {
        matchId: this.matchId,
        opponentUsername: this.opponent.name,
        scores: this.scores,
      });
      // Round 1 starts after the matchFound countdown (~3.2s)
      setTimeout(() => this.startRound(), 3200);
    }, delay);
  }

  private startRound() {
    if (this.destroyed) return;
    this.roundNumber += 1;
    this.currentWord = pick(WORD_POOL);
    this.roundId = `r_${this.roundNumber}_${Math.random().toString(36).slice(2, 6)}`;
    this.revealedState = Array(this.currentWord.length).fill(null);
    // Random reveal order
    this.revealOrder = [...Array(this.currentWord.length).keys()].sort(() => Math.random() - 0.5);
    this.tickNumber = 0;

    this.emit("startRound", {
      roundId: this.roundId,
      roundNumber: this.roundNumber,
      wordLength: this.currentWord.length,
      scores: this.scores,
    });

    // Small breath, then first tick
    setTimeout(() => this.startTick(), 600);
  }

  private startTick() {
    if (this.destroyed) return;
    this.tickNumber += 1;
    this.myGuessThisTick = false;
    this.opponentGuessThisTick = null;
    const deadline = Date.now() + TICK_DURATION_MS;

    this.emit("tickStart", {
      tickNumber: this.tickNumber,
      deadline,
      revealedState: [...this.revealedState],
    });

    // Schedule opponent guess attempt at a random moment in the tick
    this.scheduleOpponentGuess();

    // End of tick
    this.tickTimer = setTimeout(() => this.endTick(), TICK_DURATION_MS);
  }

  private scheduleOpponentGuess() {
    if (!this.opponent) return;
    const op = this.opponent;
    if (Math.random() > op.guessChance) return;
    const at = 1200 + Math.random() * (TICK_DURATION_MS - 1800);
    this.opponentTimer = setTimeout(() => {
      if (this.destroyed) return;
      const revealedCount = this.revealedState.filter(Boolean).length;
      const canGuess = revealedCount >= op.minRevealed;
      const isCorrect = canGuess && Math.random() < op.guessAccuracy;
      this.opponentGuessThisTick = { correct: isCorrect };
      this.emit("opponentGuessed", { tickNumber: this.tickNumber });
    }, at);
  }

  private handleSubmitGuess(guessText: string | undefined) {
    if (!this.roundId) return;
    if (this.myGuessThisTick) {
      this.emit("error", { code: "ALREADY_GUESSED", message: "Already submitted this tick" });
      return;
    }
    this.myGuessThisTick = true;
    const guess = (guessText ?? "").trim().toUpperCase();
    if (!guess) {
      this.emit("error", { code: "INVALID_GUESS", message: "Empty guess" });
      this.myGuessThisTick = false;
      return;
    }
    const meCorrect = guess === this.currentWord;
    // Resolve immediately (don't wait for tick end) if anyone got it right
    const opCorrect = this.opponentGuessThisTick?.correct ?? false;
    if (meCorrect || opCorrect) {
      this.resolveTick(meCorrect, opCorrect);
    }
    // If wrong and tick not yet over, wait for tick to end normally
  }

  private endTick() {
    // Resolve based on what happened this tick
    const meCorrect = false; // wrong guesses already submitted produce nothing
    const opCorrect = this.opponentGuessThisTick?.correct ?? false;
    if (opCorrect) {
      this.resolveTick(meCorrect, opCorrect);
      return;
    }
    // Reveal one more letter, then either continue or end the round
    const next = this.revealOrder.shift();
    if (next !== undefined) {
      this.revealedState[next] = this.currentWord[next];
      this.emit("revealTile", {
        index: next,
        letter: this.currentWord[next],
        revealedState: [...this.revealedState],
      });
    }
    const allRevealed = this.revealedState.every(Boolean);
    if (allRevealed) {
      // No winner round
      this.emit("roundEnd", {
        winner: null,
        revealedWord: this.currentWord,
        scores: this.scores,
        isDraw: false,
      });
      this.scheduleNextRoundOrEnd();
    } else {
      // Brief gap, then next tick
      setTimeout(() => this.startTick(), 350);
    }
  }

  private resolveTick(meCorrect: boolean, opCorrect: boolean) {
    if (this.tickTimer) clearTimeout(this.tickTimer);
    if (this.opponentTimer) clearTimeout(this.opponentTimer);

    let winner: "me" | "opponent" | "draw" | null = null;
    let isDraw = false;
    if (meCorrect && opCorrect) {
      isDraw = true;
      winner = "draw";
      this.scores = {
        me: this.scores.me + 1,
        opponent: this.scores.opponent + 1,
      };
    } else if (meCorrect) {
      winner = "me";
      this.scores = { ...this.scores, me: this.scores.me + 1 };
    } else if (opCorrect) {
      winner = "opponent";
      this.scores = { ...this.scores, opponent: this.scores.opponent + 1 };
    }

    // Reveal full word
    for (let i = 0; i < this.currentWord.length; i++) {
      this.revealedState[i] = this.currentWord[i];
    }

    this.emit("roundEnd", {
      winner,
      revealedWord: this.currentWord,
      scores: this.scores,
      isDraw,
    });

    this.scheduleNextRoundOrEnd();
  }

  private scheduleNextRoundOrEnd() {
    setTimeout(() => {
      if (this.destroyed) return;
      if (this.roundNumber >= TOTAL_ROUNDS) {
        let winner: "me" | "opponent" | "draw";
        if (this.scores.me > this.scores.opponent) winner = "me";
        else if (this.scores.opponent > this.scores.me) winner = "opponent";
        else winner = "draw";
        this.emit("matchEnd", {
          winner,
          finalScores: this.scores,
          totalRounds: TOTAL_ROUNDS,
        });
      } else {
        this.startRound();
      }
    }, ROUND_END_DELAY_MS);
  }
}
