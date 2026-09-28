import React from "react";

type Props = {
  code: string;
  language?: string;
  highlightLine?: number;
};

export const CodeLayer: React.FC<Props> = ({ code, language = "tsx", highlightLine }) => {
  return (
    <pre
      style={{
        position: "absolute",
        top: 80,
        left: 80,
        right: 80,
        padding: 24,
        background: "rgba(15, 23, 42, 0.92)",
        color: "#e2e8f0",
        borderRadius: 12,
        fontFamily:
          "ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, monospace",
        fontSize: 22,
        lineHeight: 1.4,
        whiteSpace: "pre",
        overflow: "auto",
      }}
    >
      <code>{`// ${language}\n${code}`}</code>
    </pre>
  );
};
