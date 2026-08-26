/**
 * A dark, pill-shaped tooltip bubble with a small pointer tail — drop it as
 * the LAST child inside an icon button (the button needs `position:
 * relative` or `position: absolute`, see globals.css's `.tooltip-bubble`
 * rule) rather than wrapping the button, so it never disturbs a trigger
 * that's already positioned relative to some other ancestor (e.g. the
 * Active Matters sort trigger, which is absolutely positioned within its
 * own toggle box).
 */
export function TooltipBubble({ label }: { label: string }) {
  return (
    <span className="tooltip-bubble" role="tooltip">
      {label}
    </span>
  );
}
