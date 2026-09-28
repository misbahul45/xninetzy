import React from "react";

type Props = {
  title: string;
  subtitle?: string;
};

export const TitleCard: React.FC<Props> = ({ title, subtitle }) => {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background:
          "radial-gradient(circle at 30% 20%, rgba(99,102,241,0.35), transparent 60%), radial-gradient(circle at 70% 80%, rgba(236,72,153,0.25), transparent 60%)",
        color: "#ffffff",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <div
        style={{
          fontSize: 96,
          fontWeight: 800,
          letterSpacing: -2,
          textAlign: "center",
          textShadow: "0 8px 30px rgba(0,0,0,0.6)",
        }}
      >
        {title}
      </div>
      {subtitle && (
        <div style={{ fontSize: 36, marginTop: 16, opacity: 0.85 }}>{subtitle}</div>
      )}
    </div>
  );
};
