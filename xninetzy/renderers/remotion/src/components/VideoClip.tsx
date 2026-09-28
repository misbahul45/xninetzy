import React from "react";

type Style = Record<string, number>;

type ClipLike = {
  clip_id: string;
  asset_id?: string | null;
  source_path?: string | null;
  text_overlay?: string | null;
};

type Props = {
  clip: ClipLike;
  style: Style;
};

export const VideoClipLayer: React.FC<Props> = ({ clip, style }) => {
  const transform = toTransform(style);
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
        transform,
        overflow: "hidden",
      }}
    >
      <video src={src} muted style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

function toTransform(style: Style): string {
  const parts: string[] = [];
  if (style.scale && style.scale !== 1) parts.push(`scale(${style.scale})`);
  if (style.rotation) parts.push(`rotate(${style.rotation}deg)`);
  return parts.length ? parts.join(" ") : "none";
}
