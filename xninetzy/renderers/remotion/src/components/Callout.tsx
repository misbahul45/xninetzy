import React from "react";

type Props = {
  title: string;
  x?: number;
  y?: number;
};

export const Callout: React.FC<Props> = ({ title, x = 40, y = 40 }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        padding: "12px 20px",
        background: "rgba(99, 102, 241, 0.92)",
        color: "#ffffff",
        borderRadius: 999,
        fontFamily: "Inter, system-ui, sans-serif",
        fontSize: 18,
        fontWeight: 600,
        boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
      }}
    >
      {title}
    </div>
  );
};
