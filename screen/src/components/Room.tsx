import "./Room.css";

// The painting's light filling the room: a blurred copy behind everything, tinted by --glow (set by App).
export function Room({ image }: { image: string | null }) {
  return (
    <div className="room" aria-hidden>
      {image && (
        <img key={image} className="room__blur" src={image} alt="" onError={(e) => (e.currentTarget.style.display = "none")} />
      )}
    </div>
  );
}
