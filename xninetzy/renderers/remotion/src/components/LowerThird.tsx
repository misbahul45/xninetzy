import React from "react";

type Props = {
  title: string;
  subtitle?: string;
};

export const LowerThird: React.FC<Props> = ({ title, subtitle }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        bottom: 80,
        padding: "16px 32px",
        background: "linear-gradient(90deg, rgba(15,23,42,0.85), rgba(15,23,42,0))",
        color: "#ffffff",
        fontFamily: "Inter, system-ui, sans-serif",
        width: "70%",
      }}
    >
      <div style={{ fontSize: 36, fontWeight: 700 }}>{title}</div>
      {subtitle && (
        <div style={{ fontSize: 20, opacity: 0.85, marginTop: 4 }}>{subtitle}</div>
      )}
    </div>
  );
};
