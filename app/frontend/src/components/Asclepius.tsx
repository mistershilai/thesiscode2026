/**
 * Faded Asclepius (Rod of Asclepius) background symbol.
 * Accepts `beating` prop to pulse when the solver is running.
 */
export default function Asclepius({ beating = false }: { beating?: boolean }) {
  return (
    <div className={`asclepius-wrap${beating ? " asclepius-beating" : ""}`}>
      <svg
        viewBox="0 0 200 520"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="asclepius-svg"
      >
        {/* Rod */}
        <line x1="100" y1="40" x2="100" y2="500" stroke="currentColor" strokeWidth="6" strokeLinecap="round" />

        {/* Serpent body — smooth S-curves wrapping the rod */}
        <path
          d="M100 440
             C 60 420, 60 390, 100 370
             C 140 350, 140 320, 100 300
             C 60 280, 60 250, 100 230
             C 140 210, 140 180, 100 160
             C 60 140, 60 110, 100 90"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
          fill="none"
        />

        {/* Serpent head */}
        <ellipse cx="100" cy="78" rx="12" ry="16" fill="currentColor" />
        <circle cx="95" cy="73" r="2.5" fill="#050a18" />

        {/* Rod finial — small sphere on top */}
        <circle cx="100" cy="40" r="8" fill="currentColor" />
      </svg>
    </div>
  );
}
