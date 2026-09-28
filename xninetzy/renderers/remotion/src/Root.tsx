import { Composition } from "remotion";
import React from "react";
import { loadProject } from "./runtime/loadProject";
import { ProjectDemo } from "./compositions/ProjectDemo";
import { Tutorial } from "./compositions/Tutorial";
import { DevelopmentVideo } from "./compositions/DevelopmentVideo";
import { MotionGraphic } from "./compositions/MotionGraphic";

export const RemotionRoot: React.FC = () => {
  const { render, composition } = React.useMemo(() => loadProject(), []);
  const width = render.width;
  const height = render.height;
  const fps = render.fps;
  const duration = render.duration_frames;

  return (
    <>
      <Composition
        id="ProjectDemo"
        component={ProjectDemo as React.ComponentType<unknown>}
        durationInFrames={duration}
        fps={fps}
        width={width}
        height={height}
      />
      <Composition
        id="Tutorial"
        component={Tutorial as React.ComponentType<unknown>}
        durationInFrames={duration}
        fps={fps}
        width={width}
        height={height}
      />
      <Composition
        id="DevelopmentVideo"
        component={DevelopmentVideo as React.ComponentType<unknown>}
        durationInFrames={duration}
        fps={fps}
        width={width}
        height={height}
      />
      <Composition
        id="MotionGraphic"
        component={MotionGraphic as React.ComponentType<unknown>}
        durationInFrames={duration}
        fps={fps}
        width={width}
        height={height}
      />
    </>
  );
};
