import { ActivityBar } from "./components/ActivityBar";
import { Board } from "./components/Board";
import { PaintingView } from "./components/PaintingView";
import { Transcript } from "./components/Transcript";
import { useScreenState } from "./useScreenState";

export function App() {
  const { state, online } = useScreenState();
  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Tactile Art Guide</h1>
          <p className="tagline">Audience view: what the visitor hears and feels, live.</p>
        </div>
        <span className={`pill ${online ? "on" : "off"}`}>{online ? "Live" : "Waiting for main.py"}</span>
      </header>
      <main className="stage">
        <PaintingView painting={state?.painting ?? null} section={state?.section ?? null} />
        <Board section={state?.section ?? null} hardware={state?.hardware ?? false} />
        <Transcript lines={state?.transcript ?? []} />
      </main>
      {state && <ActivityBar activity={state.activity} />}
    </div>
  );
}
