import React from "react";

type Style = Record<string, number>;

type ClipLike = {
  clip_id: string;
  text_overlay?: string | null;
  source_path?: string | null;
};

type Props = {
  clip: ClipLike;
  style: Style;
};

export const TextLayer: React.FC<Props> = ({ clip, style }) => {
  const text = clip.text_overlay ?? "";
  return (
    <div
      style={{
        position: "absolute",
        left: `${style.x ?? 0}px`,
        top: `${style.y ?? 0}px`,
        opacity: style.opacity ?? 1,
        transform: style.scale && style.scale !== 1 ? `scale(${style.scale})` : "none",
        fontFamily: "Inter, system-ui, sans-serif",
        fontSize: 48,
        fontWeight: 700,
        color: "#ffffff",
        textShadow: "0 2px 8px rgba(0,0,0,0.6)",
        padding: "8px 16px",
        maxWidth: "80%",
      }}
    >
      {text}
    </div>
  );
};
