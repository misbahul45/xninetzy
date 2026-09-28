import React from "react";
import { AbsoluteFill } from "remotion";
import { loadProject } from "../runtime/loadProject";
import { loadTimeline } from "../runtime/loadTimeline";
import { Scene } from "../components/Scene";
import { TitleCard } from "../components/_titlecard";
import { LowerThird } from "../components/LowerThird";
import { BrowserFrame } from "../components/BrowserFrame";
import { Callout } from "../components/Callout";

export const ProjectDemo: React.FC = () => {
  const data = loadProject();
  const timeline = loadTimeline(data.scenes);
  return (
    <AbsoluteFill style={{ backgroundColor: data.composition?.background_color ?? "#000000" }}>
      <TitleCard title={data.project_name} subtitle={data.project_id} />
      {timeline.map((scene, idx) => (
        <Scene key={scene.scene_id} scene={scene} sceneIndex={idx} />
      ))}
      <LowerThird title={data.project_name} subtitle="xninetzy deterministic render" />
      <Callout title="v1" x={40} y={40} />
      <BrowserFrame width={1200} height={675}>
        <AbsoluteFill style={{ background: "rgba(15,23,42,0.6)" }} />
      </BrowserFrame>
    </AbsoluteFill>
  );
};
