# Design System — Legal AI Assistant

Single light theme for v1 (no dark mode — not required by Requirements; revisit only if users ask). Visual language: calm, administrative, trustworthy — the primary target user is a lawyer with low software confidence (Charter Goal 4), so components favor clarity and predictability over decoration.

## 1. Color Tokens

**Neutrals** — backgrounds, text, borders, disabled states.

| Token | Hex | Used for |
|---|---|---|
| `--color-neutral-0` | `#FFFFFF` | Surface background (cards, modals, inputs). |
| `--color-neutral-50` | `#F8F9FA` | Page background. |
| `--color-neutral-100` | `#F1F3F5` | Hover background, disabled field background, secondary surface. |
| `--color-neutral-200` | `#E9ECEF` | Default card/panel border, disabled field border. |
| `--color-neutral-300` | `#DEE2E6` | Default input/control border. |
| `--color-neutral-400` | `#CED4DA` | Hover border, disabled text. |
| `--color-neutral-500` | `#ADB5BD` | Placeholder text. |
| `--color-neutral-600` | `#868E96` | Muted/tertiary text, inactive icons. |
| `--color-neutral-700` | `#495057` | Secondary text, secondary-button text. |
| `--color-neutral-800` | `#343A40` | Strong body text. |
| `--color-neutral-900` | `#212529` | Primary text, headings. |

**Brand** — primary interactive color.

| Token | Hex | Used for |
|---|---|---|
| `--color-brand-50` | `#EFF6FF` | Selected-row/tab tint background. |
| `--color-brand-100` | `#DBEAFE` | Hover tint on brand-tinted surfaces. |
| `--color-brand-200` | `#BFDBFE` | Focus-ring glow color. |
| `--color-brand-300` | `#93C5FD` | Selected-card border. |
| `--color-brand-500` | `#3B7DD8` | Links, icons, focus border — not used as a button fill (insufficient contrast for white text). |
| `--color-brand-600` | `#2A63B8` | Primary button default fill, active-nav accent, active-tab underline. |
| `--color-brand-700` | `#1D4E93` | Primary button hover, link hover. |
| `--color-brand-800` | `#163B70` | Primary button active/pressed. |

Brand-600/700/800 are used wherever white text sits on the fill — each meets ≥ 4.5:1 contrast against white. Brand-500 is reserved for text/icons/borders on light backgrounds, where it meets ≥ 4.5:1 against white/neutral-50.

**Semantic** — status and feedback. Each has a fill (`base`, for icons/dots), a soft `bg`, a `border`, and a `text` tuned for readability on its own `bg`.

| Token | Hex | Used for |
|---|---|---|
| `--color-success-base` | `#2F9E44` | Success icon/dot. |
| `--color-success-bg` | `#EBFBEE` | Success badge/alert background — Document "Ready," Deadline "Complete." |
| `--color-success-border` | `#B2F2BB` | Success badge/alert border. |
| `--color-success-text` | `#2B8A3E` | Success badge/alert text. |
| `--color-warning-base` | `#F59F00` | Warning icon/dot. |
| `--color-warning-bg` | `#FFF9DB` | Warning badge/alert background — Document "Draft." |
| `--color-warning-border` | `#FFE066` | Warning badge/alert border. |
| `--color-warning-text` | `#E67700` | Warning badge/alert text. |
| `--color-error-base` | `#E03131` | Error icon/dot, destructive-button default fill. |
| `--color-error-bg` | `#FFF5F5` | Error badge/alert/input background — Document "Failed," Deadline "Overdue," field validation. |
| `--color-error-border` | `#FFC9C9` | Error badge/alert border. |
| `--color-error-text` | `#C92A2A` | Error badge/alert/helper text; also destructive-button hover fill. |
| `--color-error-active` | `#A61E1E` | Destructive-button active/pressed fill. |
| `--color-info-base` | `#339AF0` | Info icon/dot. |
| `--color-info-bg` | `#E7F5FF` | Info badge background — Matter "Open," Document "Processing," Deadline "Upcoming." |
| `--color-info-border` | `#A5D8FF` | Info badge border. |
| `--color-info-text` | `#1864AB` | Info badge text. |

**Aliases** — semantic roles composed from the tables above; components reference these, not raw hex.

| Token | Value | Used for |
|---|---|---|
| `--color-bg-page` | `--color-neutral-50` | App background behind all screens. |
| `--color-bg-surface` | `--color-neutral-0` | Cards, modals, panels, inputs. |
| `--color-bg-surface-hover` | `--color-neutral-100` | Hover state on rows, ghost buttons, nav items. |
| `--color-bg-selected` | `--color-brand-50` | Selected/current nav item, highlighted row. |
| `--color-text-primary` | `--color-neutral-900` | Body text, headings. |
| `--color-text-secondary` | `--color-neutral-700` | Secondary text, labels. |
| `--color-text-tertiary` | `--color-neutral-600` | Timestamps, metadata, placeholder-adjacent text. |
| `--color-text-disabled` | `--color-neutral-400` | Disabled text everywhere. |
| `--color-text-on-brand` | `--color-neutral-0` | Text on filled brand/error buttons. |
| `--color-text-link` | `--color-brand-600` | Inline links, citation links. |
| `--color-text-link-hover` | `--color-brand-700` | Link hover. |
| `--color-border-default` | `--color-neutral-300` | Input/control borders. |
| `--color-border-strong` | `--color-neutral-400` | Hovered input/control borders. |
| `--color-border-focus` | `--color-brand-500` | Focused input/control border. |

## 2. Typography

**Families**

| Token | Stack | Used for |
|---|---|---|
| `--font-family-ui` | `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif` | All UI text, including headings. |
| `--font-family-heading` | same as `--font-family-ui` | Headings reuse the UI face at heavier weight rather than a second display font — keeps the app feeling calm/administrative and avoids a second webfont dependency (matches the solo/low-budget constraint). |
| `--font-family-mono` | `'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace` | AI Assistant citations (document name + page ref), timestamps, IDs. |

**Type scale** — fixed; do not interpolate between steps.

| Token | Size | Line-height | Default weight | Usage |
|---|---|---|---|---|
| `--font-size-xs` | 12px / 0.75rem | 1.4 | 400 | Timestamps, citation refs, helper/error text, badge labels. |
| `--font-size-sm` | 14px / 0.875rem | 1.5 | 400 | Table body, form labels, secondary text, button labels (md size). |
| `--font-size-base` | 16px / 1rem | 1.5 | 400 | Body text, chat messages, default paragraph. |
| `--font-size-md` | 18px / 1.125rem | 1.5 | 500 | Card titles, section labels, emphasized body. |
| `--font-size-lg` | 20px / 1.25rem | 1.3 | 600 | H3, modal titles. |
| `--font-size-xl` | 24px / 1.5rem | 1.25 | 600 | H2, screen section headers. |
| `--font-size-2xl` | 30px / 1.875rem | 1.2 | 700 | H1, page titles (e.g. "Matter Detail"). |
| `--font-size-3xl` | 38px / 2.375rem | 1.15 | 700 | Empty-state hero text, onboarding headline (rare). |

**Weights:** `--font-weight-regular: 400` · `--font-weight-medium: 500` · `--font-weight-semibold: 600` · `--font-weight-bold: 700`

## 3. Spacing Scale

Base unit 4px. Fixed set — no arbitrary values in component code.

| Token | Value | Typical use |
|---|---|---|
| `--space-1` | 4px | Icon-to-label gap, hairline gaps. |
| `--space-2` | 8px | Badge padding, tight control padding. |
| `--space-3` | 12px | Input horizontal padding, compact list-row padding. |
| `--space-4` | 16px | Default card padding, gap between form fields. |
| `--space-5` | 24px | Gap between sections within a screen. |
| `--space-6` | 32px | Page-level horizontal margin (desktop). |
| `--space-7` | 48px | Space above major page headers, empty-state spacing. |
| `--space-8` | 64px | Large empty-state top spacing. |
| `--space-9` | 96px | Rare — top-level hero spacing (e.g. Sign Up screen). |

**Radius & elevation** — foundational scales referenced by components in §4.

| Token | Value | Used for |
|---|---|---|
| `--radius-sm` | 4px | Inputs. |
| `--radius-md` | 8px | Buttons. |
| `--radius-lg` | 12px | Cards, modals. |
| `--radius-full` | 9999px | Badges, pill controls. |
| `--shadow-sm` | `0 1px 2px rgba(16,24,40,0.06)` | Resting cards. |
| `--shadow-md` | `0 4px 12px rgba(16,24,40,0.10)` | Hovered cards, dropdowns, notification panel. |
| `--shadow-lg` | `0 12px 32px rgba(16,24,40,0.16)` | Modals, popovers. |
| `--focus-ring` | `0 0 0 3px var(--color-brand-200)` | Default keyboard-focus glow, paired with `--color-border-focus`. |
| `--focus-ring-error` | `0 0 0 3px var(--color-error-bg)` | Focus glow on an invalid field. |

## 4. Core Components

### Buttons

Base: `border-radius: var(--radius-md)`; `font-weight: var(--font-weight-medium)`; `transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease`.

Sizes: **sm** — height 32px, padding `0 var(--space-3)`, `--font-size-xs` · **md (default)** — height 40px, padding `0 var(--space-4)`, `--font-size-sm` · **lg** — height 48px, padding `0 var(--space-5)`, `--font-size-base`.

| Variant | State | Background | Text | Border |
|---|---|---|---|---|
| Primary | default | `--color-brand-600` | `--color-text-on-brand` | none |
| | hover | `--color-brand-700` | `--color-text-on-brand` | none |
| | active | `--color-brand-800` | `--color-text-on-brand` | none |
| | focus-visible | `--color-brand-600` | `--color-text-on-brand` | `box-shadow: var(--focus-ring)` |
| | disabled | `--color-neutral-200` | `--color-text-disabled` | none, `cursor: not-allowed` |
| | loading | `--color-brand-600` (unchanged) | spinner replaces label, `pointer-events: none` | none |
| Secondary | default | `--color-bg-surface` | `--color-neutral-800` | `1px solid var(--color-border-default)` |
| | hover | `--color-bg-surface-hover` | `--color-neutral-800` | `1px solid var(--color-border-strong)` |
| | active | `--color-neutral-200` | `--color-neutral-800` | `1px solid var(--color-border-strong)` |
| | focus-visible | `--color-bg-surface` | `--color-neutral-800` | `1px solid var(--color-border-focus)`, `box-shadow: var(--focus-ring)` |
| | disabled | `--color-bg-surface` | `--color-text-disabled` | `1px solid var(--color-neutral-200)`, `cursor: not-allowed` |
| Ghost | default | transparent | `--color-neutral-700` | none |
| | hover | `--color-bg-surface-hover` | `--color-neutral-900` | none |
| | active | `--color-neutral-200` | `--color-neutral-900` | none |
| | focus-visible | transparent | `--color-neutral-700` | `box-shadow: var(--focus-ring)` |
| | disabled | transparent | `--color-text-disabled` | none, `cursor: not-allowed` |
| Destructive | default | `--color-error-base` | `--color-text-on-brand` | none |
| | hover | `--color-error-text` (#C92A2A) | `--color-text-on-brand` | none |
| | active | `--color-error-active` | `--color-text-on-brand` | none |
| | focus-visible | `--color-error-base` | `--color-text-on-brand` | `box-shadow: var(--focus-ring-error)` |
| | disabled | `--color-neutral-200` | `--color-text-disabled` | none, `cursor: not-allowed` |

### Form Inputs (text field, select, textarea)

Base: height 40px (single-line), padding `0 var(--space-3)`, `border-radius: var(--radius-sm)`, `font-size: var(--font-size-sm)`, `transition: border-color 150ms ease, box-shadow 150ms ease`.

| State | Background | Border | Text / Placeholder |
|---|---|---|---|
| default | `--color-bg-surface` | `1px solid var(--color-border-default)` | text `--color-text-primary`; placeholder `--color-neutral-500` |
| hover | `--color-bg-surface` | `1px solid var(--color-border-strong)` | unchanged |
| focus | `--color-bg-surface` | `1px solid var(--color-border-focus)`, `box-shadow: var(--focus-ring)` | unchanged |
| disabled | `--color-neutral-100` | `1px solid var(--color-neutral-200)` | text `--color-text-disabled`, `cursor: not-allowed` |
| read-only | `--color-neutral-50` | `1px solid var(--color-neutral-200)` | text `--color-text-secondary`, no focus ring on interaction |
| error | `--color-bg-surface` | `1px solid var(--color-error-base)` | helper text below field in `--color-error-text`; if focused, `box-shadow: var(--focus-ring-error)` |

### Cards

Base: `background: var(--color-bg-surface)`, `border-radius: var(--radius-lg)`, `padding: var(--space-4)`, `transition: border-color 150ms ease, box-shadow 150ms ease`.

| State | Border | Shadow | Notes |
|---|---|---|---|
| default | `1px solid var(--color-neutral-200)` | `--shadow-sm` | Static or non-interactive card. |
| hover (interactive/clickable) | `1px solid var(--color-neutral-300)` | `--shadow-md` | `cursor: pointer`. |
| focus-visible (keyboard) | `1px solid var(--color-border-focus)` | `var(--shadow-sm), var(--focus-ring)` | Row/card reachable by Tab. |
| selected | `1px solid var(--color-brand-300)` | `--shadow-sm` | Background also switches to `--color-bg-selected`. |

### Badges

Base: `border-radius: var(--radius-full)`, `padding: 2px var(--space-2)`, `font-size: var(--font-size-xs)`, `font-weight: var(--font-weight-medium)`, `border: 1px solid`.

| Variant | Background | Border | Text | Used for |
|---|---|---|---|---|
| Neutral | `--color-neutral-100` | `--color-neutral-300` | `--color-neutral-700` | Matter "Closed." |
| Info | `--color-info-bg` | `--color-info-border` | `--color-info-text` | Matter "Open," Document "Processing," Deadline "Upcoming." |
| Success | `--color-success-bg` | `--color-success-border` | `--color-success-text` | Document "Ready," Deadline "Complete." |
| Warning | `--color-warning-bg` | `--color-warning-border` | `--color-warning-text` | Document "Draft." |
| Error | `--color-error-bg` | `--color-error-border` | `--color-error-text` | Document "Failed," Deadline "Overdue." |

### Navigation

**Sidebar item** (Dashboard / Clients / Matters — §3 of the UX doc)

| State | Background | Text / Icon | Accent |
|---|---|---|---|
| default | transparent | `--color-neutral-700` | none |
| hover | `--color-bg-surface-hover` | `--color-neutral-900` | none |
| active/current | `--color-bg-selected` | `--color-brand-700` | `3px solid var(--color-brand-600)` left border |
| focus-visible | transparent | `--color-neutral-700` | `box-shadow: var(--focus-ring)` |

**Tabs** (Documents / Chat / Deadlines within Matter Detail)

| State | Text | Border-bottom |
|---|---|---|
| default | `--color-neutral-600` | `2px solid transparent` |
| hover | `--color-neutral-900` | `2px solid transparent` |
| active/selected | `--color-brand-700`, `font-weight: var(--font-weight-medium)` | `2px solid var(--color-brand-600)` |
| focus-visible | current-state color | add `box-shadow: var(--focus-ring)` |
| disabled (e.g. Chat tab before a document is Ready) | `--color-text-disabled` | `2px solid transparent`, `cursor: not-allowed` |

## 5. CSS Custom Properties

```css
:root {
  /* Neutrals */
  --color-neutral-0: #FFFFFF;
  --color-neutral-50: #F8F9FA;
  --color-neutral-100: #F1F3F5;
  --color-neutral-200: #E9ECEF;
  --color-neutral-300: #DEE2E6;
  --color-neutral-400: #CED4DA;
  --color-neutral-500: #ADB5BD;
  --color-neutral-600: #868E96;
  --color-neutral-700: #495057;
  --color-neutral-800: #343A40;
  --color-neutral-900: #212529;

  /* Brand */
  --color-brand-50: #EFF6FF;
  --color-brand-100: #DBEAFE;
  --color-brand-200: #BFDBFE;
  --color-brand-300: #93C5FD;
  --color-brand-500: #3B7DD8;
  --color-brand-600: #2A63B8;
  --color-brand-700: #1D4E93;
  --color-brand-800: #163B70;

  /* Semantic */
  --color-success-base: #2F9E44;
  --color-success-bg: #EBFBEE;
  --color-success-border: #B2F2BB;
  --color-success-text: #2B8A3E;

  --color-warning-base: #F59F00;
  --color-warning-bg: #FFF9DB;
  --color-warning-border: #FFE066;
  --color-warning-text: #E67700;

  --color-error-base: #E03131;
  --color-error-bg: #FFF5F5;
  --color-error-border: #FFC9C9;
  --color-error-text: #C92A2A;
  --color-error-active: #A61E1E;

  --color-info-base: #339AF0;
  --color-info-bg: #E7F5FF;
  --color-info-border: #A5D8FF;
  --color-info-text: #1864AB;

  /* Aliases */
  --color-bg-page: var(--color-neutral-50);
  --color-bg-surface: var(--color-neutral-0);
  --color-bg-surface-hover: var(--color-neutral-100);
  --color-bg-selected: var(--color-brand-50);
  --color-text-primary: var(--color-neutral-900);
  --color-text-secondary: var(--color-neutral-700);
  --color-text-tertiary: var(--color-neutral-600);
  --color-text-disabled: var(--color-neutral-400);
  --color-text-on-brand: var(--color-neutral-0);
  --color-text-link: var(--color-brand-600);
  --color-text-link-hover: var(--color-brand-700);
  --color-border-default: var(--color-neutral-300);
  --color-border-strong: var(--color-neutral-400);
  --color-border-focus: var(--color-brand-500);

  /* Typography */
  --font-family-ui: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-family-heading: var(--font-family-ui);
  --font-family-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace;

  --font-size-xs: 0.75rem;   /* 12px */
  --font-size-sm: 0.875rem;  /* 14px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-md: 1.125rem;  /* 18px */
  --font-size-lg: 1.25rem;   /* 20px */
  --font-size-xl: 1.5rem;    /* 24px */
  --font-size-2xl: 1.875rem; /* 30px */
  --font-size-3xl: 2.375rem; /* 38px */

  --line-height-xs: 1.4;
  --line-height-sm: 1.5;
  --line-height-base: 1.5;
  --line-height-md: 1.5;
  --line-height-lg: 1.3;
  --line-height-xl: 1.25;
  --line-height-2xl: 1.2;
  --line-height-3xl: 1.15;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* Spacing */
  --space-1: 0.25rem; /* 4px */
  --space-2: 0.5rem;  /* 8px */
  --space-3: 0.75rem; /* 12px */
  --space-4: 1rem;    /* 16px */
  --space-5: 1.5rem;  /* 24px */
  --space-6: 2rem;    /* 32px */
  --space-7: 3rem;    /* 48px */
  --space-8: 4rem;    /* 64px */
  --space-9: 6rem;    /* 96px */

  /* Radius & elevation */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,0.06);
  --shadow-md: 0 4px 12px rgba(16,24,40,0.10);
  --shadow-lg: 0 12px 32px rgba(16,24,40,0.16);
  --focus-ring: 0 0 0 3px var(--color-brand-200);
  --focus-ring-error: 0 0 0 3px var(--color-error-bg);

  /* Component: Button */
  --button-radius: var(--radius-md);
  --button-height-sm: 32px;
  --button-height-md: 40px;
  --button-height-lg: 48px;

  --button-primary-bg: var(--color-brand-600);
  --button-primary-bg-hover: var(--color-brand-700);
  --button-primary-bg-active: var(--color-brand-800);
  --button-primary-bg-disabled: var(--color-neutral-200);
  --button-primary-text: var(--color-text-on-brand);
  --button-primary-text-disabled: var(--color-text-disabled);

  --button-secondary-bg: var(--color-bg-surface);
  --button-secondary-bg-hover: var(--color-bg-surface-hover);
  --button-secondary-bg-active: var(--color-neutral-200);
  --button-secondary-border: var(--color-border-default);
  --button-secondary-border-hover: var(--color-border-strong);
  --button-secondary-text: var(--color-neutral-800);

  --button-ghost-bg-hover: var(--color-bg-surface-hover);
  --button-ghost-bg-active: var(--color-neutral-200);
  --button-ghost-text: var(--color-neutral-700);
  --button-ghost-text-hover: var(--color-neutral-900);

  --button-destructive-bg: var(--color-error-base);
  --button-destructive-bg-hover: var(--color-error-text);
  --button-destructive-bg-active: var(--color-error-active);

  /* Component: Input */
  --input-height: 40px;
  --input-radius: var(--radius-sm);
  --input-bg: var(--color-bg-surface);
  --input-bg-disabled: var(--color-neutral-100);
  --input-bg-readonly: var(--color-neutral-50);
  --input-border: var(--color-border-default);
  --input-border-hover: var(--color-border-strong);
  --input-border-focus: var(--color-border-focus);
  --input-border-error: var(--color-error-base);
  --input-placeholder: var(--color-neutral-500);

  /* Component: Card */
  --card-radius: var(--radius-lg);
  --card-padding: var(--space-4);
  --card-bg: var(--color-bg-surface);
  --card-border: var(--color-neutral-200);
  --card-border-hover: var(--color-neutral-300);
  --card-border-selected: var(--color-brand-300);
  --card-shadow: var(--shadow-sm);
  --card-shadow-hover: var(--shadow-md);

  /* Component: Badge */
  --badge-radius: var(--radius-full);
  --badge-padding: 2px var(--space-2);

  /* Component: Nav */
  --nav-item-bg-hover: var(--color-bg-surface-hover);
  --nav-item-bg-active: var(--color-bg-selected);
  --nav-item-text: var(--color-neutral-700);
  --nav-item-text-active: var(--color-brand-700);
  --nav-item-accent-active: var(--color-brand-600);

  --tab-text: var(--color-neutral-600);
  --tab-text-hover: var(--color-neutral-900);
  --tab-text-active: var(--color-brand-700);
  --tab-border-active: var(--color-brand-600);
  --tab-text-disabled: var(--color-text-disabled);
}
```
