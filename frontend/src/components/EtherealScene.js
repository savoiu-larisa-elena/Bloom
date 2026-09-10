export function EtherealScene({ children, className = '', variant = 'full' }) {
  const rootClass = ['ethereal-scene', `ethereal-scene--${variant}`, className]
    .filter(Boolean)
    .join(' ');

  if (variant === 'minimal') {
    return <div className={rootClass}>{children}</div>;
  }

  return (
    <div className={rootClass}>
      <div className="ethereal-sparkles" aria-hidden />
      <div className="ethereal-sparkles ethereal-sparkles--rose" aria-hidden />
      <div className="ethereal-sparkles ethereal-sparkles--fine" aria-hidden />
      <FairyFireflies />
      <div className="ethereal-petals" aria-hidden>
        <span className="ethereal-petal ethereal-petal--1" />
        <span className="ethereal-petal ethereal-petal--2" />
        <span className="ethereal-petal ethereal-petal--3" />
        <span className="ethereal-petal ethereal-petal--4" />
        <span className="ethereal-petal ethereal-petal--5" />
        <span className="ethereal-petal ethereal-petal--6" />
        <span className="ethereal-petal ethereal-petal--7" />
      </div>
      <FairyWisp aria-hidden />
      <div className="ethereal-veil" aria-hidden />
      {children}
    </div>
  );
}

function FairyFireflies() {
  return (
    <div className="fairy-fireflies" aria-hidden>
      <span className="fairy-firefly fairy-firefly--1" />
      <span className="fairy-firefly fairy-firefly--2" />
      <span className="fairy-firefly fairy-firefly--3" />
      <span className="fairy-firefly fairy-firefly--4" />
      <span className="fairy-firefly fairy-firefly--5" />
      <span className="fairy-firefly fairy-firefly--6" />
    </div>
  );
}

function FairyWisp({ ...props }) {
  return (
    <svg
      className="fairy-wisp"
      viewBox="0 0 120 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <path
        d="M18 52c8-18 22-28 38-30 10-1 18 4 22 14 2 5 1 11-3 15-6 7-16 10-26 8-12-2-22-10-28-22-2-4-3-8-3-12z"
        fill="currentColor"
        opacity="0.12"
      />
      <path
        d="M72 28c14 2 24 12 28 26 1 4 0 9-3 12-5 6-14 8-22 5-10-4-18-14-20-26-1-6 0-12 3-17 3-4 8-6 14-6z"
        fill="currentColor"
        opacity="0.09"
      />
      <circle cx="44" cy="38" r="2.5" fill="currentColor" opacity="0.35" />
    </svg>
  );
}

export function FairyDivider({ label }) {
  return (
    <div className="fairy-divider" aria-hidden>
      <span className="fairy-divider-vine" />
      <span className="fairy-divider-gem">✦</span>
      {label ? <span className="fairy-divider-label">{label}</span> : null}
      <span className="fairy-divider-gem">✦</span>
      <span className="fairy-divider-vine fairy-divider-vine--flip" />
    </div>
  );
}

export function GlassCard({ children, className = '', fairy = true }) {
  const rootClass = ['glass-card', fairy ? 'glass-card--fairy' : '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={rootClass}>
      <span className="glass-card-vine glass-card-vine--top" aria-hidden />
      <span className="glass-card-ornament glass-card-ornament--tl" aria-hidden>
        ✦
      </span>
      <span className="glass-card-ornament glass-card-ornament--tr" aria-hidden>
        ✧
      </span>
      <span className="glass-card-ornament glass-card-ornament--bl" aria-hidden>
        ✧
      </span>
      <span className="glass-card-ornament glass-card-ornament--br" aria-hidden>
        ✦
      </span>
      <div className="glass-card-shimmer" aria-hidden />
      {children}
    </div>
  );
}
