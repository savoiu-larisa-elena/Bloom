import { useId } from 'react';

const SHAPES = {
  classic:
    'M32 76 C28 66 18 54 14 38 C10 24 12 12 20 8 C24 5 28 4 32 6 C36 4 40 5 44 8 C52 12 54 24 50 38 C46 54 36 66 32 76 Z',
  wide:
    'M32 74 C24 64 12 50 10 34 C8 18 14 8 24 6 C28 5 30 4 32 5 C34 4 36 5 40 6 C50 8 56 18 54 34 C52 50 40 64 32 74 Z',
  narrow:
    'M32 78 C30 68 22 56 18 40 C14 26 16 14 22 9 C26 6 29 5 32 6 C35 5 38 6 42 9 C48 14 50 26 46 40 C42 56 34 68 32 78 Z',
  curled:
    'M32 77 C27 67 16 55 13 38 C10 22 14 10 22 7 C26 5 29 4 32 5 C35 4 38 5 42 7 C50 10 54 22 51 38 C48 55 37 67 32 77 Z',
};

function PetalDefs({ prefix }) {
  return (
    <defs>
      <radialGradient id={`${prefix}-surface`} cx="32%" cy="22%" r="78%">
        <stop offset="0%" stopColor="var(--rose-highlight)" />
        <stop offset="38%" stopColor="var(--rose-petal-light)" />
        <stop offset="72%" stopColor="var(--rose-petal-mid)" />
        <stop offset="100%" stopColor="var(--rose-petal-deep)" />
      </radialGradient>
      <linearGradient id={`${prefix}-fold`} x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="var(--rose-petal-mid)" stopOpacity="0" />
        <stop offset="55%" stopColor="var(--rose-petal-deep)" stopOpacity="0.45" />
        <stop offset="100%" stopColor="var(--rose-shadow)" stopOpacity="0.65" />
      </linearGradient>
      <linearGradient id={`${prefix}-edge`} x1="50%" y1="0%" x2="50%" y2="100%">
        <stop offset="0%" stopColor="var(--rose-highlight)" stopOpacity="0.85" />
        <stop offset="100%" stopColor="var(--rose-petal-light)" stopOpacity="0.2" />
      </linearGradient>
      <linearGradient id={`${prefix}-vein`} x1="50%" y1="100%" x2="50%" y2="0%">
        <stop offset="0%" stopColor="var(--rose-petal-deep)" stopOpacity="0.55" />
        <stop offset="45%" stopColor="var(--rose-petal-mid)" stopOpacity="0.35" />
        <stop offset="100%" stopColor="var(--rose-highlight)" stopOpacity="0.15" />
      </linearGradient>
    </defs>
  );
}

function PetalVeins({ prefix, variant }) {
  const curl = variant === 'curled';
  return (
    <g className="rose-petal-veins" stroke={`url(#${prefix}-vein)`} fill="none" strokeLinecap="round">
      <path strokeWidth="0.55" d="M32 73 C32 52 32 32 32 8" />
      <path strokeWidth="0.35" opacity="0.7" d="M32 58 C26 48 20 36 17 24" />
      <path strokeWidth="0.35" opacity="0.7" d="M32 58 C38 48 44 36 47 24" />
      <path strokeWidth="0.28" opacity="0.5" d="M32 44 C28 38 24 30 22 22" />
      <path strokeWidth="0.28" opacity="0.5" d="M32 44 C36 38 40 30 42 22" />
      {curl && (
        <path
          strokeWidth="0.3"
          opacity="0.45"
          d="M36 50 C40 42 44 32 46 20"
          stroke={`url(#${prefix}-fold)`}
        />
      )}
    </g>
  );
}

function PetalBody({ prefix, variant }) {
  const shape = SHAPES[variant] || SHAPES.classic;
  const curl = variant === 'curled';

  return (
    <g>
      <path className="rose-petal-body" d={shape} fill={`url(#${prefix}-surface)`} />
      <path
        className="rose-petal-fold"
        d="M32 74 C36 62 42 48 44 34 C46 22 44 12 38 8 C42 18 41 32 38 46 C36 58 34 66 32 74 Z"
        fill={`url(#${prefix}-fold)`}
        opacity={curl ? 0.72 : 0.38}
      />
      <path
        className="rose-petal-lobe-left"
        d="M32 6 C28 5 22 8 18 14 C16 18 15 22 16 26 C18 20 22 14 28 10 C30 8 31 7 32 6 Z"
        fill={`url(#${prefix}-edge)`}
        opacity="0.55"
      />
      <path
        className="rose-petal-lobe-right"
        d="M32 6 C36 5 42 8 46 14 C48 18 49 22 48 26 C46 20 42 14 36 10 C34 8 33 7 32 6 Z"
        fill={`url(#${prefix}-edge)`}
        opacity="0.48"
      />
      <path
        className="rose-petal-rim"
        d={shape}
        fill="none"
        stroke="color-mix(in srgb, var(--rose-petal-deep) 28%, transparent)"
        strokeWidth="0.4"
        opacity="0.65"
      />
      <ellipse
        className="rose-petal-base"
        cx="32"
        cy="74"
        rx="3.2"
        ry="2"
        fill="color-mix(in srgb, var(--rose-shadow) 70%, var(--rose-petal-deep) 30%)"
        opacity="0.75"
      />
      <PetalVeins prefix={prefix} variant={variant} />
    </g>
  );
}

export function RosePetal({ variant = 'classic', style, className = '' }) {
  const uid = useId().replace(/:/g, '');
  const shape = SHAPES[variant] ? variant : 'classic';

  return (
    <svg
      className={`garden-petal-svg ${className}`.trim()}
      style={style}
      viewBox="0 0 64 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <PetalDefs prefix={uid} />
      <PetalBody prefix={uid} variant={shape} />
    </svg>
  );
}
