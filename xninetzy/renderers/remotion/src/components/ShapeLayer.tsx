import React from "react";

type Style = Record<string, number>;

type ClipLike = {
  clip_id: string;
  source_path?: string | null;
};

type Props = {
  clip: ClipLike;
  style: Style;
};

export const ShapeLayer: React.FC<Props> = ({ clip, style }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: `${style.x ?? 0}px`,
        top: `${style.y ?? 0}px`,
        width: `${style.width ?? 120}px`,
        height: `${style.height ?? 120}px`,
        opacity: style.opacity ?? 1,
        transform: style.scale && style.scale !== 1 ? `scale(${style.scale})` : "none",
        backgroundColor: clip.source_path ?? "#4f46e5",
        borderRadius: 12,
      }}
    />
  );
};
