import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Line, Section } from "../types";
import type { Pixels } from "./colors";
import { shouldFly, type Shown } from "./flow";
import { formatClock } from "./format";
import { reducedMotion } from "./motion";
import { speechState, type Speech } from "./speaker";
import { NO_VISITS, visit } from "./visited";

const SAMPLE_WIDTH = 200; // enough pixels for a 10x10 grid inside small parts

/** The painting's pixels, read once per image. Null while loading or if the canvas can't be read. */
export function usePaintingPixels(src: string | null): Pixels | null {
  const [pixels, setPixels] = useState<Pixels | null>(null);
  useEffect(() => {
    setPixels(null);
    if (!src) return;
    let alive = true;
    const img = new Image();
    img.onload = () => {
      try {
        const w = SAMPLE_WIDTH;
        const h = Math.max(1, Math.round((img.naturalHeight * w) / img.naturalWidth));
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(img, 0, 0, w, h);
        if (alive) setPixels(ctx.getImageData(0, 0, w, h));
      } catch {
        // tainted canvas: callers fall back to lantern
      }
    };
    img.src = src;
    return () => {
      alive = false;
    };
  }, [src]);
  return pixels;
}

/** Who is talking, inferred from when the newest transcript line last changed. */
export function useSpeaker(lines: Line[], thinking: boolean): Speech {
  const last = lines[lines.length - 1];
  const key = last ? `${lines.length}:${last.text}` : "";
  const [changedAt, setChangedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false; // lines already on screen when the page opens are not "speaking"
      return;
    }
    if (key) setChangedAt(Date.now());
  }, [key]);
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(t);
  }, []);
  return speechState(changedAt, now, thinking);
}

/** Section numbers shown for the current painting, in order. */
export function useVisited(title: string | null, number: number | null): number[] {
  const [v, setV] = useState(NO_VISITS);
  useEffect(() => setV((prev) => visit(prev, title, number)), [title, number]);
  return v.numbers;
}

/** Starts the Borderless flow when the part changes; `held` keeps the board's balls down until it lands. */
export function useFlow(title: string | null, section: Section | null) {
  const [flowFor, setFlowFor] = useState<Section | null>(null);
  const prev = useRef<Shown>({ title: null, number: null });
  const number = section?.number ?? null;
  useLayoutEffect(() => {
    const next = { title, number };
    if (section && shouldFly(prev.current, next) && !reducedMotion()) setFlowFor(section);
    prev.current = next;
  }, [title, number]); // section is read for this render only; a new object with the same number must not re-fly
  const landed = useCallback(() => setFlowFor(null), []);
  return { flowFor, held: flowFor !== null, landed };
}

/** "03:12" since this tab first saw main.py online. */
export function useSessionClock(online: boolean): string {
  const start = useRef<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  if (online && start.current === null) start.current = Date.now();
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return formatClock(start.current === null ? 0 : now - start.current);
}
