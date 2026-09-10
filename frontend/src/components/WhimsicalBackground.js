import { RosePetal } from './RosePetal';

const VARIANTS = ['classic', 'wide', 'narrow', 'curled', 'classic', 'wide'];
const FLY_TONES = ['gold', 'rose', 'gold', 'rose', 'gold'];

function scatter(seed) {
  const value = Math.sin(seed * 127.1 + seed * 311.7) * 43758.5453;
  return value - Math.floor(value);
}

function wander(seed, spread) {
  return (scatter(seed) - 0.5) * spread;
}

function pxWander(seed, spread) {
  return `${Math.round(wander(seed, spread))}px`;
}

function generateFloatingPetals(count = 30) {
  return Array.from({ length: count }, (_, index) => {
    const r1 = scatter(index + 1);
    const r2 = scatter(index + 41);
    const r3 = scatter(index + 89);
    const r4 = scatter(index + 173);
    const r5 = scatter(index + 251);
    const r6 = scatter(index + 337);

    const left = 8 + r1 * 84;
    const top = 8 + r2 * 84;
    const scale = 0.4 + r3 * 0.45;
    const rotate = r4 * 360;
    const variant = VARIANTS[Math.floor(r5 * VARIANTS.length)];
    const layer = scale < 0.55 ? 'far' : scale < 0.72 ? 'mid' : 'near';
    const floatDuration = 28 + r6 * 22;
    const floatDelay = -r2 * 30;
    const wanderStyle = index % 3;

    return {
      id: `p-${index}`,
      left,
      top,
      scale,
      rotate,
      variant,
      layer,
      floatDuration,
      floatDelay,
      wanderStyle,
      wanderX1: `${wander(index + 401, 36)}vw`,
      wanderY1: `${wander(index + 402, 28)}vh`,
      wanderX2: `${wander(index + 403, 42)}vw`,
      wanderY2: `${wander(index + 404, 32)}vh`,
      wanderX3: `${wander(index + 405, 38)}vw`,
      wanderY3: `${wander(index + 406, 26)}vh`,
    };
  });
}

function generateFireflies(count = 32) {
  return Array.from({ length: count }, (_, index) => {
    const r1 = scatter(index + 701);
    const r2 = scatter(index + 741);
    const r3 = scatter(index + 789);
    const r4 = scatter(index + 811);
    const r5 = scatter(index + 853);
    const spread = 48 + r3 * 40;

    return {
      id: `fly-${index}`,
      left: 4 + r1 * 92,
      top: 4 + r2 * 92,
      size: 3 + r3 * 3,
      tone: FLY_TONES[Math.floor(r4 * FLY_TONES.length)],
      duration: 9 + r5 * 12,
      delay: -r2 * 18,
      wanderStyle: index % 2,
      flyX1: pxWander(index + 901, spread),
      flyY1: pxWander(index + 902, -spread * 0.9),
      flyX2: pxWander(index + 903, -spread * 0.75),
      flyY2: pxWander(index + 904, -spread * 1.1),
      flyX3: pxWander(index + 905, spread * 0.85),
      flyY3: pxWander(index + 906, -spread * 0.55),
    };
  });
}

const FLOATING_PETALS = generateFloatingPetals(30);
const FIREFLIES = generateFireflies(16);

export function WhimsicalBackground() {
  return (
    <div className="whimsy-bg garden-bg" aria-hidden>
      <div className="garden-fireflies">
        {FIREFLIES.map((fly) => (
          <span
            key={fly.id}
            className={`garden-firefly garden-firefly--${fly.tone} garden-firefly--wander-${fly.wanderStyle}`}
            style={{
              left: `${fly.left}%`,
              top: `${fly.top}%`,
              '--fly-size': `${fly.size}px`,
              '--fly-duration': `${fly.duration}s`,
              '--fly-delay': `${fly.delay}s`,
              '--fly-x1': fly.flyX1,
              '--fly-y1': fly.flyY1,
              '--fly-x2': fly.flyX2,
              '--fly-y2': fly.flyY2,
              '--fly-x3': fly.flyX3,
              '--fly-y3': fly.flyY3,
            }}
          />
        ))}
      </div>

      <div className="garden-field">
        {FLOATING_PETALS.map((petal) => (
          <span
            key={petal.id}
            className={`garden-petal-wrap garden-petal-wrap--${petal.layer} garden-petal-wrap--wander-${petal.wanderStyle}`}
            style={{
              left: `${petal.left}%`,
              top: `${petal.top}%`,
              '--petal-scale': petal.scale,
              '--petal-rotate': `${petal.rotate}deg`,
              '--float-duration': `${petal.floatDuration}s`,
              '--float-delay': `${petal.floatDelay}s`,
              '--wander-x1': petal.wanderX1,
              '--wander-y1': petal.wanderY1,
              '--wander-x2': petal.wanderX2,
              '--wander-y2': petal.wanderY2,
              '--wander-x3': petal.wanderX3,
              '--wander-y3': petal.wanderY3,
            }}
          >
            <RosePetal variant={petal.variant} />
          </span>
        ))}
      </div>
    </div>
  );
}
