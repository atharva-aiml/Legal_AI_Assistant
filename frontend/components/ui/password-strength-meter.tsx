"use client";

/**
 * Client-side-only signal (I-05) — a nudge toward a stronger password, not
 * an enforcement point. `AuthService.register`'s server-side 8-character
 * minimum remains the real, only enforced rule; this never blocks submit.
 */
function computeStrength(password: string): { score: 0 | 1 | 2 | 3 | 4; label: string } {
  if (password.length === 0) return { score: 0, label: "" };

  let criteria = 0;
  if (password.length >= 8) criteria++;
  if (password.length >= 12) criteria++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) criteria++;
  if (/[0-9]/.test(password)) criteria++;
  if (/[^A-Za-z0-9]/.test(password)) criteria++;

  if (criteria <= 1) return { score: 1, label: "Weak" };
  if (criteria === 2) return { score: 2, label: "Fair" };
  if (criteria <= 4) return { score: 3, label: "Good" };
  return { score: 4, label: "Strong" };
}

const COLOR: Record<number, string> = {
  1: "var(--color-error-base)",
  2: "var(--color-warning-base)",
  3: "var(--color-success-base)",
  4: "var(--color-success-base)",
};

export function PasswordStrengthMeter({ password }: { password: string }) {
  const { score, label } = computeStrength(password);
  if (password.length === 0) return null;

  return (
    <div style={{ marginTop: "var(--space-2)" }} aria-live="polite">
      <div style={{ display: "flex", gap: 4 }}>
        {[1, 2, 3, 4].map((segment) => (
          <span
            key={segment}
            aria-hidden="true"
            style={{
              flex: 1,
              height: 4,
              borderRadius: "var(--radius-full)",
              background: segment <= score ? COLOR[score] : "var(--color-neutral-200)",
              transition: "background-color 150ms ease",
            }}
          />
        ))}
      </div>
      <div className="text-xs" style={{ marginTop: "var(--space-1)", color: COLOR[score] }}>
        {label}
      </div>
    </div>
  );
}
