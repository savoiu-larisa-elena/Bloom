function RoseDefs() {
  return (
    <defs>
      <radialGradient id="rose-petal-outer" cx="35%" cy="30%" r="75%">
        <stop offset="0%" stopColor="var(--rose-highlight)" />
        <stop offset="45%" stopColor="var(--rose-petal-mid)" />
        <stop offset="100%" stopColor="var(--rose-petal-deep)" />
      </radialGradient>
      <radialGradient id="rose-petal-inner" cx="40%" cy="35%" r="70%">
        <stop offset="0%" stopColor="var(--rose-highlight)" />
        <stop offset="55%" stopColor="var(--rose-petal-light)" />
        <stop offset="100%" stopColor="var(--rose-petal-mid)" />
      </radialGradient>
      <radialGradient id="rose-petal-shadow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="var(--rose-petal-deep)" />
        <stop offset="100%" stopColor="var(--rose-shadow)" />
      </radialGradient>
      <filter id="rose-soft" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="1" stdDeviation="1.2" floodColor="var(--rose-shadow)" floodOpacity="0.35" />
      </filter>
    </defs>
  );
}

function Petal({ d, fill = 'url(#rose-petal-outer)', opacity = 1, transform }) {
  return (
    <path
      className="rose-petal"
      d={d}
      fill={fill}
      opacity={opacity}
      transform={transform}
    />
  );
}

const OUTER = 'M24 37 C12 33 7 22 9 13 C11 6 18 5 24 9 C30 5 37 6 39 13 C41 22 36 33 24 37 Z';
const MID = 'M24 34 C17 31 14 24 16 17 C18 12 22 11 24 14 C26 11 30 12 32 17 C34 24 31 31 24 34 Z';
const INNER = 'M24 31 C20 29 18 24 19 19 C20 15 22 14 24 16 C26 14 28 15 29 19 C30 24 28 29 24 31 Z';
const CURL = 'M24 28 C22 26 21 23 22 20 C23 17 24 16 25 18 C26 20 26 24 24 28 Z';

function BloomRose() {
  const outerAngles = [0, 74, 148, 222, 296];
  const midAngles = [38, 112, 186, 260, 334];

  return (
    <g filter="url(#rose-soft)">
      <ellipse className="rose-base-shadow" cx="24" cy="27" rx="13" ry="11" />
      {outerAngles.map((angle, i) => (
        <Petal
          key={`o-${angle}`}
          d={OUTER}
          opacity={0.96 - i * 0.02}
          transform={`rotate(${angle - 2 + i} 24 24)`}
        />
      ))}
      {midAngles.map((angle, i) => (
        <Petal
          key={`m-${angle}`}
          d={MID}
          fill="url(#rose-petal-inner)"
          opacity={0.92 - i * 0.015}
          transform={`rotate(${angle + 1} 24 24)`}
        />
      ))}
      {[10, 98, 186, 274].map((angle) => (
        <Petal key={`i-${angle}`} d={INNER} fill="url(#rose-petal-inner)" transform={`rotate(${angle} 24 24)`} />
      ))}
      <Petal d={CURL} fill="url(#rose-petal-shadow)" transform="rotate(6 24 24)" />
      <Petal d={CURL} fill="url(#rose-petal-shadow)" transform="rotate(96 24 24)" />
      <circle className="rose-center" cx="24" cy="22" r="2.2" />
    </g>
  );
}

function BloomOpen() {
  const outerAngles = [0, 51, 103, 154, 206, 257, 309];

  return (
    <g filter="url(#rose-soft)">
      <ellipse className="rose-base-shadow" cx="24" cy="26" rx="15" ry="12" />
      {outerAngles.map((angle, i) => (
        <Petal
          key={`o-${angle}`}
          d="M24 38 C10 34 5 22 8 12 C10 5 17 4 24 8 C31 4 38 5 40 12 C43 22 38 34 24 38 Z"
          opacity={0.94 - i * 0.03}
          transform={`rotate(${angle} 24 24)`}
        />
      ))}
      {[25, 77, 129, 181, 233, 285, 337].map((angle) => (
        <Petal
          key={`m-${angle}`}
          d={MID}
          fill="url(#rose-petal-inner)"
          opacity={0.88}
          transform={`rotate(${angle} 24 24)`}
        />
      ))}
      <circle className="rose-center" cx="24" cy="23" r="2.8" />
      <circle className="rose-center-ring" cx="24" cy="23" r="5" />
    </g>
  );
}

function BloomBud() {
  return (
    <g filter="url(#rose-soft)">
      <ellipse className="rose-base-shadow" cx="24" cy="25" rx="9" ry="10" />
      <Petal d="M24 34 C18 30 16 22 18 15 C20 9 24 8 24 13 C24 8 28 9 30 15 C32 22 30 30 24 34 Z" opacity={0.95} />
      <Petal
        d="M24 32 C20 28 19 22 21 17 C22 13 24 12 24 15 C24 12 26 13 27 17 C29 22 28 28 24 32 Z"
        fill="url(#rose-petal-inner)"
        transform="rotate(28 24 24)"
        opacity={0.9}
      />
      <Petal
        d="M24 32 C20 28 19 22 21 17 C22 13 24 12 24 15 C24 12 26 13 27 17 C29 22 28 28 24 32 Z"
        fill="url(#rose-petal-inner)"
        transform="rotate(-24 24 24)"
        opacity={0.9}
      />
      <Petal d={INNER} fill="url(#rose-petal-shadow)" transform="rotate(4 24 24)" />
      <ellipse className="rose-bud-tip" cx="24" cy="16" rx="3.2" ry="4" />
    </g>
  );
}

function RoseBloom({ variant }) {
  if (variant === 'bud') return <BloomBud />;
  if (variant === 'open') return <BloomOpen />;
  return <BloomRose />;
}

export function GardenFlower({ variant = 'rose', style, className = '' }) {
  return (
    <svg
      className={`garden-rose-svg ${className}`.trim()}
      style={style}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <RoseDefs />
      <RoseBloom variant={variant} />
    </svg>
  );
}
