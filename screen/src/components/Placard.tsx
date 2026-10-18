import type { Painting } from "../types";
import "./Placard.css";

// Museum wall label: artist, title, year.
export function Placard({ painting }: { painting: Painting }) {
  return (
    <div className="placard">
      <p className="placard__artist">{painting.artist}</p>
      <h1 className="placard__title">{painting.title}</h1>
      {painting.year && <p className="placard__year label">{painting.year}</p>}
    </div>
  );
}
