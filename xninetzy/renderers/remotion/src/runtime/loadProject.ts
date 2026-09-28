import type { RuntimeProps, ProjectData } from "./types";

export function loadProject(): ProjectData {
  const raw = readProps();
  return normalize(raw);
}

export function normalize(raw: RuntimeProps): ProjectData {
  const render = raw.render ?? {
    width: 1920,
    height: 1080,
    fps: 30,
    duration_frames: 900,
    quality: "balanced",
    format: "mp4",
  };
  return {
    schema_version: raw.schema_version ?? "1",
    render,
    project_id: raw.project_id ?? "unnamed",
    project_name: raw.project_name ?? "Untitled",
    composition: raw.composition ?? null,
    scenes: raw.scenes ?? [],
    assets: raw.assets ?? [],
  };
}

function readProps(): RuntimeProps {
  const proc = (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process;
  const inline = proc?.env?.REMOTION_PROPS_INLINE;
  if (inline) {
    try {
      return JSON.parse(inline) as RuntimeProps;
    } catch {
      return {};
    }
  }
  return {};
}
