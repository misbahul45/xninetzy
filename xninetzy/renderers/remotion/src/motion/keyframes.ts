import { easingValue } from "./easing";
import type { EasingName, Keyframe } from "../runtime/types";

export function interpolateKeyframes(
  keyframes: Keyframe[],
  propertyName: string,
  frame: number
): number | null {
  const relevant = keyframes.filter((k) => k.property === propertyName);
  if (relevant.length === 0) return null;
  if (relevant.length === 1) return relevant[0]!.value;

  for (let i = 1; i < relevant.length; i += 1) {
    if (relevant[i]!.frame <= relevant[i - 1]!.frame) {
      throw new Error("keyframes for property must be monotonic in frame");
    }
  }

  if (frame <= relevant[0]!.frame) return relevant[0]!.value;
  if (frame >= relevant[relevant.length - 1]!.frame) {
    return relevant[relevant.length - 1]!.value;
  }

  for (let i = 1; i < relevant.length; i += 1) {
    const hi = relevant[i]!;
    if (hi.frame > frame) {
      const lo = relevant[i - 1]!;
      const span = hi.frame - lo.frame;
      const t = span > 0 ? (frame - lo.frame) / span : 0;
      const eased = easingValue(lo.easing as EasingName, t);
      return lo.value + (hi.value - lo.value) * eased;
    }
  }
  return relevant[relevant.length - 1]!.value;
}

export function applyKeyframes(
  keyframes: Keyframe[],
  base: Record<string, number>,
  frame: number
): Record<string, number> {
  const out = { ...base };
  const props = new Set(keyframes.map((k) => k.property));
  for (const prop of props) {
    const v = interpolateKeyframes(keyframes, prop, frame);
    if (v !== null) out[prop] = v;
  }
  return out;
}
