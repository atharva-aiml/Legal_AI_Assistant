import Link from "next/link";

export type BreadcrumbItem = { label: string; href?: string };

/**
 * I-55: replaces every single-level "← Back" link with the real path back
 * to the top-level list. Every ancestor segment (all but the last) is a
 * real link; the last segment is the current page, shown as plain text
 * with aria-current="page" — the standard breadcrumb convention, and how
 * "each segment a real link" is read here (a page never links to itself).
 */
export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm">
      <ol style={{ display: "flex", flexWrap: "wrap", alignItems: "center", listStyle: "none", margin: 0, padding: 0, gap: "var(--space-1)" }}>
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)", minWidth: 0 }}>
              {item.href && !isLast ? (
                <Link href={item.href} className="text-tertiary">
                  {item.label}
                </Link>
              ) : (
                <span aria-current={isLast ? "page" : undefined} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {item.label}
                </span>
              )}
              {!isLast && <span aria-hidden="true" className="text-tertiary">/</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
