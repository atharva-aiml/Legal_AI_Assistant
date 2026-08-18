/** Shared by the dashboard's Active/Recent Matters avatars and the Calendar's day-cell badges. */
export function initials(title: string): string {
  const words = title.split(/\s+/).filter((w) => w.length > 1);
  const source = words.length > 0 ? words : [title];
  const chars = source.slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "");
  return chars.join("") || "?";
}
