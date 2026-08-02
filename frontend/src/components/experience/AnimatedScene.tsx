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
  'caja-variable': CajaVariableScene,
  'espera-input': EsperaInputScene,
  'camino-condicion': CaminoCondicionScene,
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

// ── Escena: la misma caja, dos valores distintos ────────────────────────────────
// Una variable «edad» guarda 20; el chip «edad = edad + 1» se activa y el valor
// visible pasa a 21 — el NOMBRE no cambia, el valor sí. Bucle de 6 s. Con
// prefers-reduced-motion queda el cuadro estático en el primer valor.

function CajaVariableScene() {
  return (
    <div
      className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 overflow-hidden"
      role="img"
      aria-label="Animación: una caja llamada edad guarda el número 20. Al ejecutar edad = edad + 1, el mismo nombre pasa a guardar 21 — el nombre no cambia, el valor sí."
    >
      <style>{`
        @keyframes mlv-fade1 { 0%, 45% { opacity: 1; } 50%, 100% { opacity: 0; } }
        @keyframes mlv-fade2 { 0%, 45% { opacity: 0; } 50%, 100% { opacity: 1; } }
        @keyframes mlv-chip1 { 0%, 45% { opacity: 1; } 50%, 100% { opacity: 0.35; } }
        @keyframes mlv-chip2 { 0%, 45% { opacity: 0.35; } 50%, 100% { opacity: 1; } }
        .mlv-v1 { animation: mlv-fade1 6s ease-in-out infinite; }
        .mlv-v2 { animation: mlv-fade2 6s ease-in-out infinite; }
        .mlv-c1 { animation: mlv-chip1 6s linear infinite; }
        .mlv-c2 { animation: mlv-chip2 6s linear infinite; }
        @media (prefers-reduced-motion: reduce) {
          .mlv-v1, .mlv-v2, .mlv-c1, .mlv-c2 { animation: none; }
        }
      `}</style>

      <div className="px-4 pt-4 pb-2 flex flex-wrap gap-1.5">
        <span className="mlv-c1 text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5">
          edad = 20
        </span>
        <span className="mlv-c2 text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5">
          edad = edad + 1
        </span>
      </div>
      <div className="relative h-24 mx-4 mb-4 flex items-center justify-center">
        <div className="w-24 h-16 rounded-lg border-2 border-neural-violet/40 bg-neural-violet/5 flex items-center justify-center relative">
          <span className="absolute -top-5 text-[10px] font-mono text-neural-violet/80">edad</span>
          <span className="mlv-v1 absolute text-2xl font-bold text-neural-text">20</span>
          <span className="mlv-v2 absolute text-2xl font-bold text-neural-text">21</span>
        </div>
      </div>
    </div>
  )
}

// ── Escena: el programa que espera, y el que no ─────────────────────────────
// Carril A (sin input()): muestra la pregunta y sigue de inmediato — saluda
// a nadie. Carril B (con input()): muestra la misma pregunta, se DETIENE
// ("esperando tu respuesta..."), y solo cuando "escribes" y confirmas
// continúa con el saludo correcto. Bucle de 8 s. Con prefers-reduced-motion
// queda el cuadro estático en el primer fotograma de cada carril.

function EsperaInputScene() {
  return (
    <div
      className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 overflow-hidden"
      role="img"
      aria-label="Animación: el primer programa muestra ¿Cómo te llamas? y sigue de inmediato sin esperar respuesta, saludando a nadie. El segundo programa muestra la misma pregunta pero se detiene y espera hasta que el usuario escribe su nombre, y solo entonces saluda correctamente."
    >
      <style>{`
        @keyframes m1i-failgreet { 0%, 12% { opacity: 0; } 18%, 90% { opacity: 1; } 100% { opacity: 0; } }
        @keyframes m1i-waiting   { 0%, 15% { opacity: 0; } 20%, 60% { opacity: 1; } 65%, 100% { opacity: 0; } }
        @keyframes m1i-typed     { 0%, 62% { opacity: 0; } 66%, 90% { opacity: 1; } 100% { opacity: 0; } }
        @keyframes m1i-okgreet   { 0%, 70% { opacity: 0; } 76%, 90% { opacity: 1; } 100% { opacity: 0; } }
        .m1i-failgreet { animation: m1i-failgreet 8s linear infinite; }
        .m1i-waiting   { animation: m1i-waiting 8s linear infinite; }
        .m1i-typed     { animation: m1i-typed 8s linear infinite; }
        .m1i-okgreet   { animation: m1i-okgreet 8s linear infinite; }
        @media (prefers-reduced-motion: reduce) {
          .m1i-waiting, .m1i-typed, .m1i-okgreet { animation: none; opacity: 0; }
          .m1i-failgreet { animation: none; opacity: 1; }
        }
      `}</style>

      <div className="px-4 pt-4 pb-1">
        <span className="text-[10px] font-mono text-neural-muted/60">sin input()</span>
      </div>
      <div className="relative h-12 mx-4 mb-2 border-b border-dashed border-white/[0.08] flex items-center gap-2">
        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full border border-white/10 bg-white/[0.04]">
          ¿Cómo te llamas?
        </span>
        <span className="m1i-failgreet text-[11px] text-red-400">Hola, ! ✗</span>
      </div>

      <div className="px-4 pt-1 pb-1">
        <span className="text-[10px] font-mono text-neural-muted/60">con input()</span>
      </div>
      <div className="relative h-12 mx-4 mb-4 flex items-center gap-2">
        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5">
          ¿Cómo te llamas?
        </span>
        <span className="m1i-waiting text-[11px] text-neural-muted/70 italic">esperando tu respuesta…</span>
        <span className="m1i-typed text-[11px] font-mono text-neural-text">Nico ⏎</span>
        <span className="m1i-okgreet text-[11px] text-emerald-400">Hola, Nico ✓</span>
      </div>
    </div>
  )
}

// ── Escena: una condición, dos caminos posibles ─────────────────────────────
// La misma condición (temperatura > 24) se evalúa dos veces con un valor
// distinto: cuando es verdadera, se enciende el camino del if y termina en
// su acción; cuando es falsa, se enciende el camino del else y termina en
// la suya — nunca los dos a la vez. Mismo ejemplo que ya usa la práctica
// visual de este ciclo (temperatura/24), para no introducir un caso nuevo.
// Bucle de 6 s. Con prefers-reduced-motion queda el cuadro estático en el
// primer caso (condición verdadera → camino del if).

function CaminoCondicionScene() {
  return (
    <div
      className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 overflow-hidden"
      role="img"
      aria-label="Animación: la condición temperatura mayor a 24 se evalúa dos veces. Cuando es verdadera (temperatura 30), se enciende el camino del if y termina en «enciende el aire acondicionado». Cuando es falsa (temperatura 18), se enciende el camino del else y termina en «temperatura agradable». Nunca los dos caminos a la vez."
    >
      <style>{`
        @keyframes m2c-cond1     { 0%, 45% { opacity: 1; }    50%, 100% { opacity: 0.3; } }
        @keyframes m2c-cond2     { 0%, 45% { opacity: 0.3; }  50%, 100% { opacity: 1; } }
        @keyframes m2c-ifpath    { 0%, 45% { opacity: 1; }    50%, 100% { opacity: 0.25; } }
        @keyframes m2c-elsepath  { 0%, 45% { opacity: 0.25; } 50%, 100% { opacity: 1; } }
        @keyframes m2c-ifcheck   { 0%, 8%  { opacity: 0; } 14%, 45% { opacity: 1; } 50%, 100% { opacity: 0; } }
        @keyframes m2c-elsecheck { 0%, 58% { opacity: 0; } 64%, 95% { opacity: 1; } 100% { opacity: 0; } }
        .m2c-cond1     { animation: m2c-cond1 6s ease-in-out infinite; }
        .m2c-cond2     { animation: m2c-cond2 6s ease-in-out infinite; }
        .m2c-ifpath    { animation: m2c-ifpath 6s ease-in-out infinite; }
        .m2c-elsepath  { animation: m2c-elsepath 6s ease-in-out infinite; }
        .m2c-ifcheck   { animation: m2c-ifcheck 6s linear infinite; }
        .m2c-elsecheck { animation: m2c-elsecheck 6s linear infinite; }
        @media (prefers-reduced-motion: reduce) {
          .m2c-cond1, .m2c-ifpath, .m2c-ifcheck { animation: none; }
          .m2c-cond2, .m2c-elsepath, .m2c-elsecheck { animation: none; opacity: 0.25; }
          .m2c-ifcheck { opacity: 1; }
        }
      `}</style>

      <div className="px-4 pt-4 pb-3 flex justify-center">
        <span className="relative inline-block text-[11px] font-mono px-2 py-0.5 rounded-full border border-neural-glow/30 text-neural-glow bg-neural-glow/5 min-w-[15rem] text-center">
          <span className="m2c-cond1 absolute inset-0 flex items-center justify-center whitespace-nowrap">
            temperatura = 30 → &gt; 24 ✓
          </span>
          <span className="m2c-cond2 whitespace-nowrap">temperatura = 18 → &gt; 24 ✗</span>
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 px-4 pb-4">
        <div className="m2c-ifpath rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-2 py-3 text-center relative">
          <span className="text-[10px] font-mono text-neural-muted/70 block mb-1">if</span>
          <span className="text-[11px]">Enciende el aire acondicionado</span>
          <span className="m2c-ifcheck absolute top-1 right-1 text-emerald-400 text-sm font-bold">✓</span>
        </div>
        <div className="m2c-elsepath rounded-lg border border-neural-violet/30 bg-neural-violet/5 px-2 py-3 text-center relative">
          <span className="text-[10px] font-mono text-neural-muted/70 block mb-1">else</span>
          <span className="text-[11px]">Temperatura agradable</span>
          <span className="m2c-elsecheck absolute top-1 right-1 text-emerald-400 text-sm font-bold">✓</span>
        </div>
      </div>
    </div>
  )
}
