export function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="banner banner-error" role="alert">
      <span aria-hidden="true">⚠</span>
      <span>{children}</span>
    </div>
  );
}
