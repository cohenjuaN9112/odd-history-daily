// Entry point for the vertical Shorts composition (see Short.tsx). Rendered with:
//   npx remotion render src/short/index.ts Short out.mp4 --props='{"id":"<slug>"}'
import React from "react";
import { Composition, registerRoot } from "remotion";
import { FPS } from "../estilo";
import { calcularShort, Short } from "./Short";

const Raiz: React.FC = () =>
  React.createElement(Composition, {
    id: "Short",
    component: Short as never,
    calculateMetadata: calcularShort as never,
    durationInFrames: 300,
    fps: FPS,
    width: 1080,
    height: 1920,
    defaultProps: { id: "short", pista: "todo" },
  });

registerRoot(Raiz);
