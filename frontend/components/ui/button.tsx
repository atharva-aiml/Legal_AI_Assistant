import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "destructive";
type Size = "sm" | "md" | "lg";

type BaseProps = {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
  className?: string;
};

type ButtonAsButton = BaseProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> & { href?: undefined };

type ButtonAsLink = BaseProps & {
  href: string;
  disabled?: boolean;
};

function classesFor(variant: Variant, size: Size, className?: string) {
  const sizeClass = size === "sm" ? "btn-sm" : size === "lg" ? "btn-lg" : "";
  return ["btn", `btn-${variant}`, sizeClass, className].filter(Boolean).join(" ");
}

/**
 * Shared Button primitive — every screen uses this instead of hand-rolled
 * inline styles, so a primary action always looks identical everywhere.
 * Pass `href` to render as a real navigable Link styled as a button
 * (never a <button onClick={() => router.push(...)}> masquerading as a link).
 */
export function Button(props: ButtonAsButton | ButtonAsLink) {
  const { variant = "primary", size = "md", loading, children, className } = props;

  if ("href" in props && props.href) {
    const { href, disabled } = props;
    if (disabled) {
      return (
        <span className={classesFor(variant, size, className)} aria-disabled="true">
          {children}
        </span>
      );
    }
    return (
      <Link href={href} className={classesFor(variant, size, className)}>
        {children}
      </Link>
    );
  }

  const { disabled, variant: _variant, size: _size, loading: _loading, children: _children, className: _className, ...rest } = props as ButtonAsButton;
  return (
    <button className={classesFor(variant, size, className)} disabled={disabled || loading} {...rest}>
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}
