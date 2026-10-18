import { useEffect, useMemo, useRef, useState } from "react";
import { COPY } from "../design/copy";
import { createPinScene, type PinScene } from "../lib/pinScene";
import { boardField, fieldFromPixels, resample, RESOLUTIONS, type PinField, type Pixels } from "../lib/pins";
import type { Section } from "../types";
import "./PinModal.css";

function loadPixels(url: string): Promise<Pixels> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return reject(new Error("no 2d context"));
      ctx.drawImage(img, 0, 0);
      resolve(ctx.getImageData(0, 0, canvas.width, canvas.height));
    };
    img.onerror = reject;
    img.src = url;
  });
}

// Loads a section's relief once per URL pair; null until both images are in (or if either fails).
function useReliefField(relief: string | null, color: string | null): PinField | null {
  const [field, setField] = useState<PinField | null>(null);
  useEffect(() => {
    if (!relief || !color) return setField(null);
    let alive = true;
    Promise.all([loadPixels(relief), loadPixels(color)])
      .then(([h, c]) => alive && setField(fieldFromPixels(h, c)))
      .catch(() => alive && setField(null));
    return () => { alive = false; };
  }, [relief, color]);
  return field;
}

// The 10,000-pin simulation for the current section. Mounted only while open, so the scene lives exactly as long.
export function PinModal({ section, onClose }: { section: Section | null; onClose: () => void }) {
  const [step, setStep] = useState(0); // start at 10 x 10 (fewest pins)
  const n = RESOLUTIONS[step];
  const field = useReliefField(section?.relief ?? null, section?.relief_color ?? null);
  const gridKey = section?.grid.flat().join("");
  const shown = useMemo(() => {
    if (!field || !section) return null;
    const f = resample(field, n);
    return n === 10 ? boardField(f, section.grid) : f;
  }, [field, n, gridKey]); // gridKey, not section: polls create a new section object with the same grid

  const hostRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<PinScene | null>(null);
  const [noWebgl, setNoWebgl] = useState(false);
  useEffect(() => {
    if (!hostRef.current) return;
    try {
      sceneRef.current = createPinScene(hostRef.current);
    } catch {
      setNoWebgl(true);
    }
    return () => { sceneRef.current?.dispose(); sceneRef.current = null; };
  }, []);
  useEffect(() => { if (shown) sceneRef.current?.show(shown); }, [shown]);

  const message = noWebgl ? COPY.pinsNoWebgl : !section ? COPY.pinsNone : !field ? COPY.pinsMaking : null;

  return (
    <div className="pins" onClick={onClose}>
      <div className="pins__panel" role="dialog" aria-modal="true" aria-labelledby="pins-title" onClick={(e) => e.stopPropagation()}>
        <header className="pins__head">
          <div>
            <span className="label pins__kicker">{COPY.pinsTitle}</span>
            <h2 id="pins-title" className="pins__title">{section?.name ?? COPY.pinsTitle}</h2>
          </div>
          <button type="button" className="key-button label" onClick={onClose}>
            <kbd>P</kbd> {COPY.close}
          </button>
        </header>
        <div className="pins__stage">
          <div ref={hostRef} className="pins__canvas" />
          {message && <p className="pins__message">{message}</p>}
        </div>
        <footer className="pins__foot">
          <label className="pins__slider label">
            {COPY.pinsPerSide}
            <input type="range" min={0} max={RESOLUTIONS.length - 1} step={1} value={step}
                   onChange={(e) => setStep(Number(e.target.value))} />
            <span className="pins__value">{n} × {n}{n === 10 ? ` · ${COPY.pinsToday}` : ""}</span>
          </label>
          <span className="label pins__note">{COPY.pinsKicker} {COPY.pinsHint}</span>
        </footer>
      </div>
    </div>
  );
}
