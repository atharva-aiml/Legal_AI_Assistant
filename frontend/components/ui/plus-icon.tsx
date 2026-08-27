/** The single "+" glyph used by every icon-only add button (New Matter,
 * New Deadline, Add document). Styling — no border, square hover surface,
 * slight expand — lives on the button classes in globals.css. */
export function PlusIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
