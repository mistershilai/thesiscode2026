/**
 * Kaelo mark: a "K" drawn as a small supply network (nodes joined by routes),
 * after the full logo. Transparent, so it sits on either theme.
 */
export default function KaeloMark({ size = 30 }: { size?: number }) {
  return (
    <svg
      className="nav-mark"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="kaelo-mark-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#2563eb" />
        </linearGradient>
      </defs>
      <g stroke="url(#kaelo-mark-grad)" strokeWidth="2.4" strokeLinecap="round" fill="none">
        <line x1="8" y1="5" x2="8" y2="27" />
        <line x1="8" y1="20" x2="24" y2="5" />
        <line x1="14.5" y1="14" x2="24" y2="27" />
      </g>
      <g fill="url(#kaelo-mark-grad)">
        <circle cx="8" cy="5" r="3.2" />
        <circle cx="8" cy="27" r="3.2" />
        <circle cx="24" cy="5" r="3.2" />
        <circle cx="24" cy="27" r="3.2" />
      </g>
      <circle className="nav-mark-hub" cx="14.5" cy="14" r="2.6" />
    </svg>
  );
}
