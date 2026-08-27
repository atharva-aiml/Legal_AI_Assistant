"use client";

import { useEffect, useState } from "react";

/**
 * Voice-dictation visualiser — a 48-bar waveform, an elapsed timer and a
 * "Listening…" label, shown while the Web Speech recogniser is active.
 *
 * Adapted from KokonutUI's "AI Voice" (MIT — kokonutui.com,
 * github.com/kokonut-labs/kokonutui) to this codebase's plain-CSS /
 * design-token stack: no Framer Motion, no lucide-react. The mic button and
 * the recogniser lifecycle stay in ChatPanel; this component only renders
 * the animation, driven by `active`. See `.ai-voice*` in styles/globals.css.
 */
const BAR_COUNT = 48;

function formatTime(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (totalSeconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

export function AiVoiceVisualizer({ active }: { active: boolean }) {
  const [seconds, setSeconds] = useState(0);
  // Per-bar base height, randomised once on the client so the waveform
  // doesn't look mechanically uniform (mirrors the source's Math.random()
  // bars); set in an effect to avoid an SSR hydration mismatch.
  const [heights, setHeights] = useState<number[]>(() => Array.from({ length: BAR_COUNT }, () => 32));

  useEffect(() => {
    setHeights(Array.from({ length: BAR_COUNT }, () => 20 + Math.random() * 80));
  }, []);

  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [active]);

  return (
    <div className={`ai-voice${active ? " ai-voice-active" : ""}`} aria-hidden={!active}>
      <div className="ai-voice-bars">
        {heights.map((height, i) => (
          <span key={i} className="ai-voice-bar" style={{ height: `${height}%`, animationDelay: `${i * 0.05}s` }} />
        ))}
      </div>
      <div className="ai-voice-meta">
        <span className="mono ai-voice-time">{formatTime(seconds)}</span>
        <span className="ai-voice-label">Listening…</span>
      </div>
    </div>
  );
}
