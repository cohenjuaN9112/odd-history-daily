// Odd History Daily: vertical (1080x1920) Shorts drawn with the "Historia Animada" template engine.
// This file is ours; the template itself is downloaded separately and never committed here (its license
// forbids redistributing it). At build time animado/hacer.py copies this folder to <template>/src/short/.
//
// How it works: the template draws every frame on a 1920x1080 stage. We scale that stage up by 1920/1080 and
// show a 607.5 px wide vertical window of it, so everything stays vector-sharp. Each plano chooses where the
// window looks:
//   "corte": x of the window centre on the 1920 stage (default: the middle of the actors in a scene, else 960)
//   "corte_hasta": optional second x; the window glides from "corte" to it during the plano.
import React from "react";
import { AbsoluteFill, CalculateMetadataFunction, interpolate, useCurrentFrame } from "remotion";
import { calcularVideoTerra, PlanT, VideoTerra } from "../historia/VideoTerra";
import { FPS } from "../estilo";

export const K = 1920 / 1080;
export const VENTANA = 1080 / K; // 607.5 px of the stage

type Props = { id: string; pista?: "todo" | "voz" | "fondo"; plan?: PlanT };
type PlanoX = PlanT["planos"][number] & { corte?: number; corte_hasta?: number };

const centro = (p: PlanoX): number => {
  if (typeof p.corte === "number") return p.corte;
  const act = p.tipo === "escena" ? p.actores ?? [] : [];
  if (act.length) return act.reduce((a, b) => a + b.x, 0) / act.length;
  return 960;
};

const lim = (x: number) => Math.max(VENTANA / 2, Math.min(1920 - VENTANA / 2, x));

export const calcularShort: CalculateMetadataFunction<Props> = (args) => calcularVideoTerra(args as never) as never;

export const Short: React.FC<Props> = (props) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  let cx = 960;
  const planos = (props.plan?.planos ?? []) as PlanoX[];
  const p = planos.find((q) => t >= q.ini && t < q.fin) ?? planos[planos.length - 1];
  if (p) {
    const a = centro(p);
    const b = typeof p.corte_hasta === "number" ? p.corte_hasta : a;
    cx = interpolate(t, [p.ini, Math.max(p.ini + 0.01, p.fin)], [a, b], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  }
  const izquierda = lim(cx) - VENTANA / 2;
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transformOrigin: "0 0", transform: `scale(${K}) translateX(${-izquierda}px)` }}>
        <VideoTerra {...props} />
      </div>
    </AbsoluteFill>
  );
};
