import type { Painting, Section } from "../types";

export function PaintingView({ painting, section }: { painting: Painting | null; section: Section | null }) {
  if (!painting) {
    return (
      <section className="panel painting-panel empty">
        <p>No painting yet. Ask the guide for one.</p>
      </section>
    );
  }
  const [x0, y0, x1, y1] = section?.bbox ?? [0, 0, 0, 0];
  return (
    <section className="panel painting-panel">
      <h2>The painting</h2>
      <div className="frame-wrap">
        {painting.image && (
          <img
            key={painting.image}
            src={painting.image}
            alt={painting.title}
            onError={(e) => (e.currentTarget.style.display = "none")}
          />
        )}
        {section && (
          <div
            className="bbox"
            style={{
              left: `${x0 * 100}%`,
              top: `${y0 * 100}%`,
              width: `${(x1 - x0) * 100}%`,
              height: `${(y1 - y0) * 100}%`,
            }}
          />
        )}
      </div>
      <h3>{painting.title}</h3>
      <p className="meta">
        {painting.artist}
        {painting.year ? `, ${painting.year}` : ""}
      </p>
      <ol className="parts">
        {painting.sections.map((s) => (
          <li key={s.number} className={s.number === section?.number ? "current" : undefined}>
            {s.name}
          </li>
        ))}
      </ol>
    </section>
  );
}
