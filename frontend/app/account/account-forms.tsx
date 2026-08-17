"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { PasswordStrengthMeter } from "@/components/ui/password-strength-meter";

/** I-51: editing the display name — router.refresh() re-fetches the server-rendered NavBar/AccountMenu props, so the new name shows up everywhere without a full page reload. */
export function EditNameForm({ currentName }: { currentName: string }) {
  const router = useRouter();
  const [name, setName] = useState(currentName);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/me`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save your name — retry.");
      return;
    }

    setSaved(true);
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="stack-3">
      <div className="field">
        <label className="field-label" htmlFor="account-name">Name</label>
        <input
          id="account-name"
          className="input"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setSaved(false);
          }}
          required
        />
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="row" style={{ alignItems: "center", gap: "var(--space-3)" }}>
        <Button type="submit" loading={submitting} disabled={!name.trim() || name.trim() === currentName}>
          {submitting ? "Saving…" : "Save name"}
        </Button>
        {saved && <span className="text-sm" style={{ color: "var(--color-success-text)" }}>Saved</span>}
      </div>
    </form>
  );
}

/** I-51: current password re-verified server-side before a new one is ever stored (AuthService.changePassword). */
export function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setSubmitting(true);
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ currentPassword, newPassword }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't change your password — retry.");
      return;
    }

    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setSaved(true);
  }

  return (
    <form onSubmit={handleSubmit} className="stack-3">
      <div className="field">
        <label className="field-label" htmlFor="current-password">Current password</label>
        <input
          id="current-password"
          type="password"
          className="input"
          value={currentPassword}
          onChange={(e) => { setCurrentPassword(e.target.value); setSaved(false); }}
          autoComplete="current-password"
          required
        />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="new-password">New password</label>
        <input
          id="new-password"
          type="password"
          className="input"
          value={newPassword}
          onChange={(e) => { setNewPassword(e.target.value); setSaved(false); }}
          autoComplete="new-password"
          required
        />
        <PasswordStrengthMeter password={newPassword} />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="confirm-password">Confirm new password</label>
        <input
          id="confirm-password"
          type="password"
          className="input"
          value={confirmPassword}
          onChange={(e) => { setConfirmPassword(e.target.value); setSaved(false); }}
          autoComplete="new-password"
          required
        />
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="row" style={{ alignItems: "center", gap: "var(--space-3)" }}>
        <Button type="submit" loading={submitting} disabled={!currentPassword || newPassword.length < 8}>
          {submitting ? "Changing…" : "Change password"}
        </Button>
        {saved && <span className="text-sm" style={{ color: "var(--color-success-text)" }}>Password changed</span>}
      </div>
    </form>
  );
}

/** I-52: SD-006 — Deadline reminders is the only notification type today, so a single checkbox is the honest shape. */
export function NotificationPreferencesForm({ initialDeadlineRemindersEnabled }: { initialDeadlineRemindersEnabled: boolean }) {
  const [enabled, setEnabled] = useState(initialDeadlineRemindersEnabled);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleToggle(next: boolean) {
    setEnabled(next);
    setError(null);
    setSaved(false);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/me/preferences`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ deadlineRemindersEnabled: next }),
    });

    setSubmitting(false);

    if (!res.ok) {
      setEnabled(!next); // revert an optimistic toggle that didn't actually save
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save this preference — retry.");
      return;
    }

    setSaved(true);
  }

  return (
    <div className="stack-3">
      <label className="row" style={{ gap: "var(--space-2)", cursor: submitting ? "default" : "pointer" }}>
        <input
          type="checkbox"
          checked={enabled}
          disabled={submitting}
          onChange={(e) => handleToggle(e.target.checked)}
        />
        Deadline reminders
      </label>
      <div className="text-tertiary text-sm">In-app reminders as a Deadline approaches. Other Lawyers in your Firm keep getting theirs even if you turn this off.</div>

      {error && <ErrorBanner>{error}</ErrorBanner>}
      {saved && <span className="text-sm" style={{ color: "var(--color-success-text)" }}>Saved</span>}
    </div>
  );
}
