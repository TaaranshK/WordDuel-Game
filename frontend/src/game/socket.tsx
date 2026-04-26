import { createContext, useContext, useEffect, useRef, useState } from "react";

/**
 * Lightweight socket abstraction for the WordDuel backend.
 * The `.send / .on` contract matches the previous MockSocket implementation.
 */

type SocketLike = {
  send: (event: string, payload?: Record<string, unknown>) => void;
  on: (event: string, cb: (...args: unknown[]) => void) => void;
  off: (event: string, cb: (...args: unknown[]) => void) => void;
};

type ServerMessage = {
  event?: string;
  payload?: unknown;
};

class WordDuelWebSocket implements SocketLike {
  private ws: WebSocket;
  private listeners = new Map<string, Set<(...args: unknown[]) => void>>();
  private openWaiters = new Set<() => void>();
  private pending: string[] = [];

  constructor(url: string) {
    this.ws = new WebSocket(url);

    this.ws.addEventListener("open", () => {
      const pending = this.pending;
      this.pending = [];
      pending.forEach((m) => this.ws.send(m));
      this.openWaiters.forEach((w) => w());
      this.openWaiters.clear();
    });

    this.ws.addEventListener("message", (evt) => {
      let msg: ServerMessage | null = null;
      try {
        msg = JSON.parse(String(evt.data)) as ServerMessage;
      } catch {
        return;
      }

      const event = msg?.event;
      if (!event) return;

      this.listeners.get(event)?.forEach((cb) => cb(msg?.payload));
    });
  }

  destroy() {
    try {
      this.ws.close();
    } catch {
      // ignore
    }
    this.listeners.clear();
    this.openWaiters.clear();
  }

  async waitUntilOpen() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise<void>((resolve) => {
      this.openWaiters.add(resolve);
    });
  }

  send(event: string, payload?: Record<string, unknown>) {
    const msg = JSON.stringify({ event, payload });
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(msg);
      return;
    }
    if (this.ws.readyState === WebSocket.CONNECTING) {
      this.pending.push(msg);
    }
  }

  on(event: string, cb: (...args: unknown[]) => void) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(cb);
  }

  off(event: string, cb: (...args: unknown[]) => void) {
    this.listeners.get(event)?.delete(cb);
  }
}

const SocketCtx = createContext<SocketLike | null>(null);

export function SocketProvider({ children }: { children: React.ReactNode }) {
  const ref = useRef<WordDuelWebSocket | null>(null);

  if (typeof window !== "undefined" && !ref.current) {
    const url =
      (import.meta.env.VITE_BACKEND_WS_URL as string | undefined) ??
      `${window.location.protocol === "https:" ? "wss" : "ws"}://${
        window.location.hostname
      }:8000/ws/wordduel/`;

    ref.current = new WordDuelWebSocket(url);
  }

  useEffect(() => {
    return () => {
      ref.current?.destroy();
      ref.current = null;
    };
  }, []);

  if (!ref.current) return null;
  return <SocketCtx.Provider value={ref.current}>{children}</SocketCtx.Provider>;
}

export function useSocket() {
  const s = useContext(SocketCtx);
  if (!s) throw new Error("useSocket must be used inside <SocketProvider>");
  return s;
}

export function useSocketEvent<T = unknown>(event: string, handler: (payload: T) => void) {
  const socket = useSocket();
  const handlerRef = useRef(handler);
  handlerRef.current = handler;
  useEffect(() => {
    const cb = (payload: unknown) => handlerRef.current(payload as T);
    socket.on(event, cb);
    return () => socket.off(event, cb);
  }, [socket, event]);
}
