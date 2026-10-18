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
  const [wide, setWide] = useState(false); // squarish or landscape: the label wraps below, so the image must leave room for it
  const [failed, setFailed] = useState<string | null>(null); // image that failed to load: show the blank frame
  const showImage = painting.image && failed !== painting.image;
  return (
    <figure className={wide ? "stage stage--wide" : "stage"}>
      <div className="stage__frame" ref={frameRef}>
        <div className="stage__clip">
          {showImage ? (
            <img src={painting.image!} alt={painting.title} onError={() => setFailed(painting.image)}
              onLoad={(e) => setWide(e.currentTarget.naturalWidth >= 0.7 * e.currentTarget.naturalHeight)} />
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
