import React from "react";

type Props = {
  children: React.ReactNode;
  width: number;
  height: number;
};

export const BrowserFrame: React.FC<Props> = ({ children, width, height }) => {
  return (
    <div
      style={{
        position: "absolute",
        width,
        height,
        background: "linear-gradient(180deg, #1f2937 0%, #111827 100%)",
        borderRadius: 12,
        boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: 32,
          display: "flex",
          alignItems: "center",
          padding: "0 12px",
          gap: 8,
          background: "#0f172a",
        }}
      >
        <span style={{ width: 12, height: 12, background: "#ef4444", borderRadius: 6 }} />
        <span style={{ width: 12, height: 12, background: "#f59e0b", borderRadius: 6 }} />
        <span style={{ width: 12, height: 12, background: "#10b981", borderRadius: 6 }} />
      </div>
      <div style={{ position: "relative", width: "100%", height: `calc(100% - 32px)` }}>
        {children}
      </div>
    </div>
  );
};
