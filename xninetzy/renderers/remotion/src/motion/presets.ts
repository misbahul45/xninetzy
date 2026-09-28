import type { EasingName, Keyframe } from "../runtime/types";

export type PresetSpec = {
  primitive: string;
  target: string;
  start_frame: number;
  end_frame: number;
  easing: EasingName;
  parameters?: Record<string, number>;
};

export const CANONICAL_PRIMITIVES: ReadonlySet<string> = new Set<string>([
  "FadeIn", "FadeOut", "SlideIn", "SlideOut",
  "ScaleIn", "ScaleOut", "Zoom", "Pan", "Reveal",
  "Typewriter", "BlurIn", "BlurOut", "Pop",
  "Spring", "Stagger", "Highlight", "Spotlight",
  "CameraPush", "CameraPull", "KenBurns",
  "LowerThird", "TitleCard", "Callout", "CodeHighlight",
  "BrowserFrame", "DeviceFrame",
]);

export function isCanonical(primitive: string): boolean {
  return CANONICAL_PRIMITIVES.has(primitive);
}

export function primitiveToKeyframes(spec: PresetSpec): Keyframe[] {
  const { primitive, start_frame: start, end_frame: end, easing, parameters = {} } = spec;
  const span = end - start;
  if (span <= 0) {
    throw new Error("invalid motion preset frame window");
  }

  switch (primitive) {
    case "FadeIn":
      return ease("opacity", start, end, 0, 1, easing, { "0": 0 });
    case "FadeOut":
      return ease("opacity", start, end, 1, 0, easing);
    case "SlideIn": {
      const x0 = parameters["direction"] === "right" ? 1 : -1;
      return ease("x", start, end, x0, 0, easing, { [String(start)]: x0 });
    }
    case "SlideOut": {
      const x1 = parameters["direction"] === "left" ? -1 : 1;
      return ease("x", start, end, 0, x1, easing);
    }
    case "ScaleIn":
      return ease("scale", start, end, parameters["from_scale"] ?? 0.8, 1, easing);
    case "ScaleOut":
      return ease("scale", start, end, 1, parameters["to_scale"] ?? 1.2, easing);
    case "Zoom":
      return ease("scale", start, end, 1, parameters["to_scale"] ?? 1.12, easing);
    case "Pan":
      return ease(
        "x",
        start,
        end,
        parameters["from_x"] ?? 0,
        parameters["to_x"] ?? 0,
        easing
      );
    case "Reveal":
      return ease("clip_path", start, end, 0, parameters["to_clip"] ?? 1, easing);
    case "CameraPush":
      return ease("scale", start, end, 1, parameters["to_scale"] ?? 1.06, easing);
    case "CameraPull":
      return ease("scale", start, end, 1, parameters["to_scale"] ?? 0.96, easing);
    case "LowerThird":
      return ease("lowerthird_opacity", start, end, 0, 1, easing);
    case "TitleCard":
      return ease("titlecard_opacity", start, end, 0, 1, easing);
    case "BrowserFrame":
      return [{ property: "browser_chrome", frame: start, value: 1, easing }];
    case "DeviceFrame":
      return [{ property: "device_chrome", frame: start, value: 1, easing }];
    default:
      throw new Error(`primitive '${primitive}' not implemented`);
  }
}

function ease(
  property: string,
  start: number,
  end: number,
  fromValue: number,
  toValue: number,
  easing: EasingName,
  anchors: Record<string, number> = {}
): Keyframe[] {
  const steps = 4;
  const keys: Keyframe[] = [];
  if (anchors[String(start)] !== undefined) {
    keys.push({ property, frame: start, value: anchors[String(start)]!, easing });
  } else {
    keys.push({ property, frame: start, value: fromValue, easing });
  }
  for (let i = 1; i < steps; i += 1) {
    const t = i / steps;
    const frame = start + Math.round((end - start) * t);
    keys.push({ property, frame, value: fromValue, easing });
  }
  keys.push({ property, frame: end, value: toValue, easing });
  return keys;
}
