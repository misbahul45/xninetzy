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

export const ImageLayer: React.FC<Props> = ({ clip, style }) => {
  const src = clip.source_path ?? "";
  return (
    <div
      style={{
        position: "absolute",
        left: `${style.x ?? 0}px`,
        top: `${style.y ?? 0}px`,
        width: `${style.width ?? 0}px`,
        height: `${style.height ?? 0}px`,
        opacity: style.opacity ?? 1,
        transform: style.scale && style.scale !== 1 ? `scale(${style.scale})` : "none",
        backgroundImage: `url(${src})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    />
  );
};
