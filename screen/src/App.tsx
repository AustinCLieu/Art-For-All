import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { AgentDrawer } from "./components/AgentDrawer";
import { BorderlessFlow } from "./components/BorderlessFlow";
import { Captions } from "./components/Captions";
import { IdleScreen } from "./components/IdleScreen";
import { LookingUp } from "./components/LookingUp";
import { PaintingStage } from "./components/PaintingStage";
import { PinModal } from "./components/PinModal";
import { Placard } from "./components/Placard";
import { Room } from "./components/Room";
import { RenderProgress } from "./components/RenderProgress";
import { TopStrip } from "./components/TopStrip";
import { TouchBoard } from "./components/TouchBoard";
import { TourRail } from "./components/TourRail";
import { averageColor, cellColors, css, LANTERN } from "./lib/colors";
import { useFlow, usePaintingPixels, useSpeaker, useVisited } from "./lib/hooks";
import { pickScene } from "./lib/scene";
import { useScreenState } from "./useScreenState";
import "./App.css";

export function App() {
  const { state, online } = useScreenState();
  const scene = pickScene(state, online);
  const painting = state?.painting ?? null;
  const section = state?.section ?? null;

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pinsOpen, setPinsOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "s" || e.key === "S") setDrawerOpen((o) => !o);
      if (e.key === "p" || e.key === "P") setPinsOpen((o) => !o);
      if (e.key === "Escape") { setDrawerOpen(false); setPinsOpen(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const pixels = usePaintingPixels(painting?.image ?? null);
  const average = useMemo(() => (pixels ? averageColor(pixels) : LANTERN), [pixels]);
  const bboxKey = section?.bbox.join(",");
  const colors = useMemo(
    () => (pixels && section ? cellColors(pixels, section.bbox) : null),
    [pixels, bboxKey], // bboxKey, not section: polls create a new section object with the same bbox
  );
  // null until the first poll lands, so the transcript already on screen at page open isn't "speaking"
  const speech = useSpeaker(state ? state.transcript : null, state?.activity.gemini.status === "working");
  const visited = useVisited(painting?.title ?? null, section?.number ?? null);
  const { flowFor, held, landed } = useFlow(painting?.title ?? null, section);
  const frameRef = useRef<HTMLDivElement>(null);
  const wellsRef = useRef<HTMLDivElement>(null);

  return (
    <div className={`app app--${scene}`} style={{ "--glow": css(average, 0.12) } as CSSProperties}>
      <Room image={scene === "touring" ? painting?.image ?? null : null} />
      <TopStrip online={online} drawerOpen={drawerOpen} onToggleDrawer={() => setDrawerOpen((o) => !o)}
                pinsOpen={pinsOpen} onTogglePins={() => setPinsOpen((o) => !o)} />
      {state && <RenderProgress render={state.render} />}
      {scene === "offline" && <IdleScreen offline />}
      {scene === "idle" && <IdleScreen offline={false} />}
      {scene === "looking-up" && state && <LookingUp detail={state.activity.gemini.detail} />}
      {scene === "touring" && state && painting && (
        <>
          <div className="col col--art">
            <PaintingStage painting={painting} section={section} frameRef={frameRef} grid={flowFor !== null} />
            <Placard painting={painting} />
          </div>
          <div className="col col--touch">
            <TouchBoard section={section} total={painting.sections.length} hardware={state.hardware} colors={colors} held={held} wellsRef={wellsRef} />
            <Captions lines={state.transcript} speech={speech} />
          </div>
          <TourRail sections={painting.sections} current={section?.number ?? null} visited={visited} />
          {flowFor && (
            <BorderlessFlow key={flowFor.number} section={flowFor} colors={colors} frameRef={frameRef} wellsRef={wellsRef} onLanded={landed} />
          )}
        </>
      )}
      {state && <AgentDrawer open={drawerOpen} activity={state.activity} frame={section?.frame ?? null} onClose={() => setDrawerOpen(false)} />}
      {pinsOpen && <PinModal section={section} onClose={() => setPinsOpen(false)} />}
    </div>
  );
}
