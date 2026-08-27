/**
 * "AI is thinking" indicator — three dots rising and falling in a wave
 * while an answer is being generated. Pure CSS (see `.thinking-dots*` in
 * styles/globals.css); no dependencies.
 */
export function ThinkingDots() {
  return (
    <span className="thinking-dots">
      {/* One steady announcement for assistive tech; the dots are decorative. */}
      <span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
        Generating a response
      </span>
      <span className="thinking-dot" aria-hidden="true" />
      <span className="thinking-dot" aria-hidden="true" />
      <span className="thinking-dot" aria-hidden="true" />
    </span>
  );
}
