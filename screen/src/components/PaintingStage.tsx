import { useState, type RefObject } from "react";
import type { Painting, Section } from "../types";
import { SpotlightBox, SpotlightTag } from "./Spotlight";
import "./PaintingStage.css";

export function PaintingStage({ painting, section, frameRef, grid }: {
  painting: Painting;
  section: Section | null;
  frameRef: RefObject<HTMLDivElement>;
  grid: boolean;
}) {
  const [failed, setFailed] = useState<string | null>(null); // image that failed to load: show the blank frame
  const showImage = painting.image && failed !== painting.image;
  return (
    <figure className="stage">
      <div className="stage__frame" ref={frameRef}>
        <div className="stage__clip">
          {showImage ? (
            <img src={painting.image!} alt={painting.title} onError={() => setFailed(painting.image)} />
          ) : (
            <div className="stage__blank" />
          )}
          {section && <SpotlightBox bbox={section.bbox} grid={grid} />}
        </div>
        {section && <SpotlightTag section={section} />}
      </div>
    </figure>
  );
}
