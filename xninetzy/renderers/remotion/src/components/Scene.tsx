import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { SceneData } from "../runtime/types";
import { VideoClipLayer } from "./VideoClip";
import { TextLayer } from "./TextLayer";
import { ImageLayer } from "./ImageLayer";
import { ShapeLayer } from "./ShapeLayer";
import { applyKeyframes } from "../motion/keyframes";

type SceneProps = {
  scene: SceneData;
  sceneIndex: number;
};

export const Scene: React.FC<SceneProps> = ({ scene, sceneIndex }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (frame < scene.start_frame) return null;
  const localFrame = frame - scene.start_frame;
  if (localFrame >= scene.duration_frames) return null;

  return (
    <AbsoluteFill>
      {scene.transition_in && (
        <TransitionLayer
          transition={scene.transition_in}
          localFrame={localFrame}
        />
      )}
      {scene.tracks
        .slice()
        .sort((a, b) => a.z_index - b.z_index)
        .map((track) =>
          track.clips.map((clip) => {
            const raw = clip as Record<string, unknown>;
            const typedClip = raw as {
              clip_id: string;
              track_id: string;
              asset_id?: string | null;
              source_path?: string | null;
              text_overlay?: string | null;
              keyframes?: Array<{ property: string; frame: number; value: number; easing: string }>;
              x?: number;
              y?: number;
              width?: number;
              height?: number;
              opacity?: number;
              scale?: number;
              rotation?: number;
            };
            const style = applyKeyframes(
              typedClip.keyframes ?? [],
              {
                x: typedClip.x ?? 0,
                y: typedClip.y ?? 0,
                width: typedClip.width ?? 1,
                height: typedClip.height ?? 1,
                opacity: typedClip.opacity ?? 1,
                scale: typedClip.scale ?? 1,
                rotation: typedClip.rotation ?? 0,
              },
              localFrame
            );

            if (track.kind === "video") {
              return (
                <VideoClipLayer
                  key={`${sceneIndex}-${clip.clip_id}`}
                  clip={typedClip}
                  style={style}
                />
              );
            }
            if (track.kind === "text") {
              return (
                <TextLayer
                  key={`${sceneIndex}-${clip.clip_id}`}
                  clip={typedClip}
                  style={style}
                />
              );
            }
            if (track.kind === "image") {
              return (
                <ImageLayer
                  key={`${sceneIndex}-${clip.clip_id}`}
                  clip={typedClip}
                  style={style}
                />
              );
            }
            if (track.kind === "shape") {
              return (
                <ShapeLayer
                  key={`${sceneIndex}-${clip.clip_id}`}
                  clip={typedClip}
                  style={style}
                />
              );
            }
            return null;
          })
        )}
    </AbsoluteFill>
  );
};

const TransitionLayer: React.FC<{
  transition: { transition_id: string; kind: string; duration_frames: number };
  localFrame: number;
}> = ({ transition, localFrame }) => {
  if (localFrame >= transition.duration_frames) return null;
  const t = localFrame / transition.duration_frames;
  const opacity = transition.kind === "dip_to_black" ? t : 1 - t * 0.2;
  return (
    <AbsoluteFill
      style={{
        backgroundColor:
          transition.kind === "dip_to_black"
            ? `rgba(0, 0, 0, ${Math.min(1, t)})`
            : `rgba(255, 255, 255, ${Math.max(0, t * 0.2)})`,
        opacity,
      }}
    />
  );
};
