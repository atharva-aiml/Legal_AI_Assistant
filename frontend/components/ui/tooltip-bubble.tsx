/**
 * A dark, pill-shaped tooltip bubble with a small pointer tail — drop it as
 * the LAST child inside an icon button (the button needs `position:
 * relative` or `position: absolute`, see globals.css's `.tooltip-bubble`
 * rule) rather than wrapping the button, so it never disturbs a trigger
 * that's already positioned relative to some other ancestor (e.g. the
 * Active Matters sort trigger, which is absolutely positioned within its
 * own toggle box).
 *
 * Pass `below` when the trigger sits at the top edge of an overflow-hidden
 * container (e.g. the AI Chat header toolbar) so the bubble drops downward
 * into visible space instead of being clipped above.
 */
export function TooltipBubble({ label, below }: { label: string; below?: boolean }) {
  return (
    <span className={`tooltip-bubble${below ? " tooltip-bubble-below" : ""}`} role="tooltip">
      {label}
    </span>
  );
}
