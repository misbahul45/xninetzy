import React from "react";
import { AbsoluteFill } from "remotion";
import { loadProject } from "../runtime/loadProject";
import { loadTimeline } from "../runtime/loadTimeline";
import { Scene } from "../components/Scene";
import { TitleCard } from "../components/_titlecard";

export const Tutorial: React.FC = () => {
  const data = loadProject();
  const timeline = loadTimeline(data.scenes);
  return (
    <AbsoluteFill style={{ backgroundColor: data.composition?.background_color ?? "#000000" }}>
      <TitleCard title={data.project_name} subtitle="tutorial" />
      {timeline.map((scene, idx) => (
        <Scene key={scene.scene_id} scene={scene} sceneIndex={idx} />
      ))}
    </AbsoluteFill>
  );
};
