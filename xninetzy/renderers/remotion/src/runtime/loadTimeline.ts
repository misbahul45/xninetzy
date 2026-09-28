import type { SceneData } from "./types";

export function loadTimeline(scenes: SceneData[]): SceneData[] {
  return scenes
    .slice()
    .sort((a, b) => a.start_frame - b.start_frame);
}
