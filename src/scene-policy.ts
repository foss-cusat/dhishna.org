// Camera values are in glTF/Three coordinates: Blender (x, y, z) → (x, z, -y).
export const CAMERA_POSITION = [34, 45.5, 62] as const;
export const CAMERA_TARGET = [0, 6.5, 4] as const;

export function cameraSpan(width: number, height: number, mobile = false): number {
  const aspect = width / Math.max(height, 1);
  // Preserve both towers on narrow screens; avoid shrinking the campus on ultrawide displays.
  return mobile
    ? Math.max(34, 52 / Math.max(aspect, .65))
    : Math.max(39, 60 / Math.max(aspect, .5));
}

export function boundedPointer(x: number, y: number): [number, number] {
  return [Math.max(-1, Math.min(1, x)), Math.max(-1, Math.min(1, y))];
}

export function shouldAnimate(reducedMotion: boolean, visible: boolean): boolean {
  return !reducedMotion && visible;
}

export type TiltSample = { beta: number; gamma: number };

// Relative to the way the visitor is already holding the phone, in screen axes.
export function tiltPointer(sample: TiltSample, origin: TiltSample, screenAngle = 0): [number, number] {
  const values = [sample.beta, sample.gamma, origin.beta, origin.gamma, screenAngle];
  if (!values.every(Number.isFinite)) return [0, 0];
  const difference = (value: number, start: number) => ((value - start + 540) % 360) - 180;
  const pitch = difference(sample.beta, origin.beta);
  const roll = difference(sample.gamma, origin.gamma);
  const radians = screenAngle * Math.PI / 180;
  const horizontal = roll * Math.cos(radians) + pitch * Math.sin(radians);
  const vertical = pitch * Math.cos(radians) - roll * Math.sin(radians);
  // Ignore sensor noise; cap travel at a comfortable 18-degree tilt.
  const scale = (degrees: number) => Math.sign(degrees) * Math.max(0, Math.abs(degrees) - .6) / 17.4;
  return boundedPointer(scale(horizontal), scale(vertical));
}
