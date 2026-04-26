type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export type Player = {
  id: number;
  username: string;
  total_wins: number;
  total_matches: number;
  last_seen_at: string | null;
  created_at: string;
};

export type DictionaryStats = {
  total_active: number;
  easy: number;
  medium: number;
  hard: number;
};

export type MatchBriefPlayer = { id: number; username: string };

export type Match = {
  id: number;
  player1: MatchBriefPlayer;
  player2: MatchBriefPlayer;
  score1: number;
  score2: number;
  status: string;
  winner: MatchBriefPlayer | null;
  max_rounds: number;
  tick_duration_ms: number;
  created_at: string;
  updated_at: string;
};

export type JoinResponse = {
  player: Player;
  session_token: string;
};

function getBackendHttpBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_BACKEND_HTTP_URL as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/+$/, "");

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

export class BackendApiError extends Error {
  status: number;
  body: JsonValue | string | null;

  constructor(message: string, status: number, body: JsonValue | string | null) {
    super(message);
    this.name = "BackendApiError";
    this.status = status;
    this.body = body;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getBackendHttpBaseUrl();
  const url = `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;

  const resp = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const contentType = resp.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!resp.ok) {
    let body: JsonValue | string | null = null;
    try {
      body = isJson ? ((await resp.json()) as JsonValue) : await resp.text();
    } catch {
      body = null;
    }
    throw new BackendApiError(
      `Backend request failed: ${resp.status} ${resp.statusText}`,
      resp.status,
      body,
    );
  }

  if (resp.status === 204) return undefined as T;
  if (!isJson) return (await resp.text()) as T;
  return (await resp.json()) as T;
}

export async function joinPlayer(username: string): Promise<JoinResponse> {
  return requestJson<JoinResponse>("/api/accounts/join/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
}

export async function getLeaderboard(): Promise<Player[]> {
  return requestJson<Player[]>("/api/accounts/leaderboard/");
}

export async function getPlayerProfile(playerId: number): Promise<Player> {
  return requestJson<Player>(`/api/accounts/player/${playerId}/`);
}

export async function getDictionaryStats(): Promise<DictionaryStats> {
  return requestJson<DictionaryStats>("/api/dictionary/stats/");
}

export async function getMatchHistory(playerId: number): Promise<Match[]> {
  const data = await requestJson<unknown>(`/api/game/match/history/${playerId}/`);
  if (Array.isArray(data)) return data as Match[];
  return [];
}
