import { useEffect, useRef, useState } from "react";
import type { State } from "./types";

// Asks screen.py for the state a few times a second. `online` is false while main.py isn't running.
export function useScreenState(intervalMs = 300) {
  const [state, setState] = useState<State | null>(null);
  const [online, setOnline] = useState(false);
  const last = useRef("");

  useEffect(() => {
    let alive = true;
    let timer = 0;
    const poll = async () => {
      try {
        const res = await fetch("/api/state", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        if (alive && text !== last.current) {
          last.current = text; // only re-render when something changed
          setState(JSON.parse(text) as State);
        }
        if (alive) setOnline(true);
      } catch {
        if (alive) setOnline(false);
      }
      if (alive) timer = window.setTimeout(poll, intervalMs);
    };
    poll();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [intervalMs]);

  return { state, online };
}
