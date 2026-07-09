// Escenas animadas reales para los refuerzos que prometen una animación
// (PED-002: «si fuera una animación, debería ser una animación»).
// CSS puro, sin assets ni dependencias: lo suficiente para comunicar la idea.
// En S2 el Content Discovery Agent podrá sustituir la escena por un recurso
// curado real sin tocar este componente (registro por sceneId).

import type { ComponentType } from 'react'

interface SceneProps {
  sceneId: string
}

export function AnimatedScene({ sceneId }: SceneProps) {
  const Scene = SCENES[sceneId]
  return Scene ? <Scene /> : null
}

const SCENES: Record<string, ComponentType> = {
  'dos-robots': DosRobotsScene,
}

// ── Escena: dos robots, misma meta, instrucciones distintas ────────────────────
// Carril A: «cruza la habitación» (ambigua) → deambula y choca con la mesa.
// Carril B: tres instrucciones precisas que se iluminan en secuencia → llega.
// Bucle de 9 s. Con prefers-reduced-motion queda el cuadro estático con ✗/✓.

function DosRobotsScene() {
  return (
    <div
      className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 overflow-hidden"
      role="img"
      aria-label="Animación: dos robots reciben la misma meta. El que recibe «cruza la habitación» choca contra la mesa; el que recibe tres instrucciones precisas llega a la puerta."
    >
      <style>{`
        @keyframes ml1-walkA {
          0%, 8%   { left: 4%;  transform: translateY(0) rotate(0); }
          16%      { transform: translateY(-5px); }
          24%      { transform: translateY(4px); }
          32%      { transform: translateY(-4px); }
          38%      { left: 46%; transform: translateY(0); }
          41%      { left: 48%; transform: rotate(-10deg); }
          43%      { left: 47%; transform: rotate(10deg); }
          45%      { left: 48%; transform: rotate(0); }
          100%     { left: 48%; }
        }
        @keyframes ml1-fail {
          0%, 44%  { opacity: 0; }
          50%, 90% { opacity: 1; }
          100%     { opacity: 0; }
        }
        @keyframes ml1-walkB {
          0%, 14%  { left: 4%; }
          24%      { left: 21%; }  26% { left: 21%; }
          36%      { left: 39%; }  38% { left: 39%; }
          48%      { left: 57%; }  50% { left: 57%; }
          60%      { left: 74%; }
          100%     { left: 74%; }
        }
        @keyframes ml1-ok {
          0%, 62%  { opacity: 0; }
          68%, 90% { opacity: 1; }
          100%     { opacity: 0; }
        }
        @keyframes ml1-chip1 { 0%, 13% { opacity: 1; } 16%, 100% { opacity: 0.35; } }
        @keyframes ml1-chip2 { 0%, 13% { opacity: 0.35; } 16%, 58% { opacity: 1; } 62%, 100% { opacity: 0.35; } }
        @keyframes ml1-chip3 { 0%, 58% { opacity: 0.35; } 62%, 90% { opacity: 1; } 100% { opacity: 0.35; } }
        .ml1-a    { animation: ml1-walkA 9s ease-in-out infinite; }
        .ml1-b    { animation: ml1-walkB 9s ease-in-out infinite; }
        .ml1-fail { animation: ml1-fail 9s linear infinite; }
        .ml1-ok   { animation: ml1-ok 9s linear infinite; }
        .ml1-c1   { animation: ml1-chip1 9s linear infinite; }
        .ml1-c2   { animation: ml1-chip2 9s linear infinite; }
        .ml1-c3   { animation: ml1-chip3 9s linear infinite; }
        @media (prefers-reduced-motion: reduce) {
          .ml1-a, .ml1-b, .ml1-fail, .ml1-ok, .ml1-c1, .ml1-c2, .ml1-c3 { animation: none; }
        }
      `}</style>

      {/* Carril A — instrucción ambigua */}
      <div className="px-4 pt-4 pb-1">
        <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded-full border border-amber-500/30 text-amber-300/90 bg-amber-500/5">
          «Cruza la habitación»
        </span>
      </div>
      <div className="relative h-14 mx-4 border-b border-dashed border-white/[0.08]">
        <span className="ml1-a absolute top-2 text-2xl" style={{ left: '4%' }}>🤖</span>
        {/* la mesa con la que choca */}
        <div className="absolute top-4 flex flex-col items-center" style={{ left: '54%' }}>
          <div className="w-8 h-5 rounded-sm border border-white/20 bg-white/[0.06]" />
          <span className="text-[9px] font-mono text-neural-muted/60 mt-0.5">mesa</span>
        </div>
        <span className="ml1-fail absolute top-1 text-sm font-bold text-red-400" style={{ left: '51%' }}>✗</span>
      </div>

      {/* Carril B — instrucciones precisas */}
      <div className="px-4 pt-3 pb-1 flex flex-wrap gap-1.5">
        <span className="ml1-c1 text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5">
          1. Gira 90° a la izquierda
        </span>
        <span className="ml1-c2 text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5">
          2. Avanza 4 pasos
        </span>
        <span className="ml1-c3 text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5">
          3. Detente
        </span>
      </div>
      <div className="relative h-14 mx-4 mb-2">
        <span className="ml1-b absolute top-2 text-2xl" style={{ left: '4%' }}>🤖</span>
        <span className="absolute top-2 text-2xl" style={{ left: '82%' }}>🚪</span>
        <span className="ml1-ok absolute top-1 text-sm font-bold text-emerald-400" style={{ left: '79%' }}>✓</span>
      </div>
    </div>
  )
}
