export function Skeleton({ width = "100%", height = 16, circle = false }: { width?: number | string; height?: number; circle?: boolean }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: circle ? "50%" : undefined }}
      aria-hidden="true"
    />
  );
}

export function SkeletonRows({ count = 3, height = 72 }: { count?: number; height?: number }) {
  return (
    <div className="stack" role="status" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card">
          <Skeleton height={14} width="40%" />
          <div style={{ marginTop: "var(--space-2)" }}>
            <Skeleton height={12} width="65%" />
          </div>
        </div>
      ))}
      <span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>Loading…</span>
    </div>
  );
}
