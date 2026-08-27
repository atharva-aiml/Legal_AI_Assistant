/* Typography exploration canvas generator — Legal AI Assistant.
   Emits 15 .dc.html artboards (5 type systems x 3 screens) + canvas.json.
   Layout / theme / palette / background are held CONSTANT across all five;
   only the type system (family, weight, size ramp, tracking, case, text
   colour, mono usage) changes. */

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = dirname(fileURLToPath(import.meta.url));

/* ------------------------------------------------------------------ *
 * Shared design tokens + component CSS (lifted from frontend/styles/
 * globals.css — exact values, trimmed to what these three screens use)
 * ------------------------------------------------------------------ */
const BASE_CSS = `
*{box-sizing:border-box;}
:root{
  --color-neutral-0:#FFFFFF;--color-neutral-50:#F7F8F9;--color-neutral-100:#EEF0F2;
  --color-neutral-200:#E1E4E8;--color-neutral-300:#C9CED4;--color-neutral-400:#A7AEB8;
  --color-neutral-500:#838C97;--color-neutral-600:#626B76;--color-neutral-700:#48505A;
  --color-neutral-800:#313740;--color-neutral-900:#1B1F24;--color-neutral-950:#101317;
  --color-primary-50:#F4F4F5;--color-primary-100:#E4E4E7;--color-primary-200:#D4D4D8;
  --color-primary-300:#A1A1AA;--color-primary-400:#71717A;--color-primary-500:#27272A;
  --color-primary-600:#18181B;--color-primary-700:#09090B;
  --color-brand-200:var(--color-primary-200);--color-brand-300:var(--color-primary-300);
  --color-brand-600:var(--color-primary-600);--color-brand-700:var(--color-primary-700);
  --color-success-base:#1E7B4D;--color-success-bg:#E8F5EE;--color-success-border:#B7E0C7;--color-success-text:#145C39;
  --color-warning-base:#B5790A;--color-warning-bg:#FBF1DE;--color-warning-border:#EDCB86;--color-warning-text:#7A5107;
  --color-error-base:#B3261E;--color-error-bg:#FBEAE9;--color-error-border:#E9B3AF;--color-error-text:#7C1A14;
  --color-info-base:#0E7C86;--color-info-bg:#E5F3F4;--color-info-border:#A9D6DA;--color-info-text:#0A5960;
  --color-ai-50:#EFEBF7;--color-ai-200:#CFC3E8;--color-ai-500:#5B4B9E;--color-ai-700:#40356F;
  --color-citation-50:#E7F0EF;--color-citation-200:#B9D6D3;--color-citation-500:#3E6E6B;--color-citation-700:#2A4C4A;
  --color-bg-page:var(--color-neutral-50);--color-bg-surface:var(--color-neutral-0);
  --color-bg-surface-hover:var(--color-neutral-100);--color-bg-surface-sunken:var(--color-neutral-100);
  --color-bg-selected:#EFEBFB;
  --color-text-primary:var(--color-neutral-900);--color-text-secondary:var(--color-neutral-600);
  --color-text-tertiary:var(--color-neutral-500);--color-text-disabled:var(--color-neutral-400);
  --color-text-on-brand:#FFFFFF;--color-text-link:var(--color-primary-500);--color-text-link-hover:var(--color-primary-600);
  --color-border-default:var(--color-neutral-200);--color-border-strong:var(--color-neutral-300);
  --font-family-ui:'Public Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-heading:var(--font-family-ui);
  --font-family-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;
  --font-size-xs:0.75rem;--font-size-sm:0.875rem;--font-size-base:1rem;--font-size-md:1.125rem;
  --font-size-lg:1.25rem;--font-size-xl:1.5rem;--font-size-2xl:1.875rem;--font-size-3xl:2.375rem;
  --font-weight-regular:400;--font-weight-medium:500;--font-weight-semibold:600;--font-weight-bold:700;
  --space-1:0.25rem;--space-2:0.5rem;--space-3:0.75rem;--space-4:1rem;--space-5:1.5rem;--space-6:2rem;--space-7:3rem;--space-8:4rem;
  --radius-sm:6px;--radius-md:8px;--radius-lg:10px;--radius-full:9999px;
  --shadow-sm:0 1px 2px rgba(26,32,41,0.06);--shadow-md:0 4px 12px rgba(26,32,41,0.10);--shadow-lg:0 16px 40px rgba(26,32,41,0.18);
  --nav-height:64px;
}
html,body{height:100%;}
body{
  margin:0;font-family:var(--font-family-ui);
  background:linear-gradient(to left,#FFFFFF,var(--color-bg-page));
  background-attachment:fixed;color:var(--color-text-primary);
  font-size:var(--font-size-base);line-height:1.5;-webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}
h1,h2,h3,h4{font-family:var(--font-family-heading);font-weight:var(--font-weight-semibold);color:var(--color-text-primary);margin:0;line-height:1.25;}
p{margin:0;}
a{color:var(--color-text-link);text-decoration:none;}
a:hover{color:var(--color-text-link-hover);}
code,.mono{font-family:var(--font-family-mono);font-size:0.925em;}
.type-band{
  display:flex;align-items:center;gap:16px;height:36px;padding:0 var(--space-6);
  background:var(--color-neutral-100);border-bottom:1px solid var(--color-neutral-200);
  font-family:var(--font-family-mono);font-size:11px;letter-spacing:0.05em;
  text-transform:uppercase;color:var(--color-neutral-500);white-space:nowrap;
}
.type-band b{color:var(--color-neutral-900);font-weight:600;}
.type-band span{color:var(--color-neutral-300);}
.app-nav{
  display:flex;align-items:center;gap:var(--space-5);height:var(--nav-height);
  padding:0 var(--space-6);background:var(--color-bg-surface);
  border-bottom:1px solid var(--color-neutral-200);
}
.app-nav-brand{
  display:inline-flex;align-items:center;height:36px;font-family:var(--font-family-heading);
  font-weight:var(--font-weight-semibold);font-size:calc(var(--font-size-md) + 1px);
  line-height:1;color:var(--color-text-primary);white-space:nowrap;
}
.app-nav-links{display:flex;align-items:center;gap:var(--space-4);}
.app-nav-link{
  display:inline-flex;align-items:center;height:36px;line-height:1;font-size:var(--font-size-sm);
  font-weight:var(--font-weight-regular);color:var(--color-text-tertiary);
  border-bottom:2px solid transparent;
}
.app-nav-link-active{color:var(--color-text-primary);font-weight:var(--font-weight-semibold);border-bottom-color:var(--color-brand-600);}
.app-nav-search{flex:1;max-width:280px;position:relative;display:flex;align-items:center;}
.app-nav-search-input{
  width:100%;height:38px;padding:0 var(--space-3) 0 40px;border-radius:var(--radius-full);
  border:1px solid var(--color-neutral-200);background:var(--color-bg-surface);
  color:var(--color-text-primary);font-family:var(--font-family-ui);font-size:var(--font-size-sm);
}
.app-nav-search-input::placeholder{color:var(--color-neutral-500);}
.app-nav-search-icon{position:absolute;left:var(--space-3);top:50%;transform:translateY(-50%);color:var(--color-neutral-500);display:flex;}
.app-nav-actions{display:flex;align-items:center;gap:var(--space-4);margin-left:auto;color:var(--color-neutral-500);}
.acct-avatar{
  width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:var(--font-size-xs);font-weight:600;background:var(--color-primary-100);color:var(--color-primary-700);
  font-family:var(--font-family-ui);
}
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:var(--space-2);height:40px;
  padding:0 var(--space-4);border-radius:var(--radius-md);border:1px solid transparent;
  font-family:var(--font-family-ui);font-weight:var(--font-weight-medium);font-size:var(--font-size-sm);
  line-height:1;white-space:nowrap;
}
.btn-sm{height:32px;padding:0 var(--space-3);font-size:var(--font-size-xs);}
.btn-primary{background:var(--color-primary-500);color:var(--color-text-on-brand);border-color:var(--color-primary-500);}
.btn-secondary{background:var(--color-bg-surface);color:var(--color-neutral-800);border-color:var(--color-border-default);}
.btn-plain{background:transparent;border-color:transparent;color:var(--color-neutral-700);}
.card{
  background:var(--color-bg-surface);border:1px solid var(--color-neutral-200);border-radius:var(--radius-lg);
  padding:var(--space-4);box-shadow:var(--shadow-sm);
}
.badge{
  display:inline-flex;align-items:center;gap:var(--space-1);border-radius:var(--radius-full);
  padding:2px var(--space-2);font-size:var(--font-size-xs);font-weight:var(--font-weight-medium);border:1px solid;line-height:1.4;white-space:nowrap;
}
.badge-neutral{background:var(--color-neutral-100);border-color:var(--color-neutral-300);color:var(--color-neutral-700);}
.badge-success{background:var(--color-success-bg);border-color:var(--color-success-border);color:var(--color-success-text);}
.badge-warning{background:var(--color-warning-bg);border-color:var(--color-warning-border);color:var(--color-warning-text);}
.badge-ai{background:var(--color-ai-50);border-color:var(--color-ai-200);color:var(--color-ai-700);}
.status-dot-badge{display:inline-flex;align-items:center;gap:var(--space-2);font-size:var(--font-size-sm);color:var(--color-text-primary);white-space:nowrap;}
.status-dot{width:8px;height:8px;border-radius:var(--radius-full);flex-shrink:0;}
.status-dot-open{background:var(--color-success-base);}
.status-dot-closed{background:var(--color-neutral-400);}
.row{display:flex;align-items:center;gap:var(--space-3);}
.row-between{display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);}
.stack{display:flex;flex-direction:column;gap:var(--space-3);}
.text-secondary{color:var(--color-text-secondary);}
.text-tertiary{color:var(--color-text-tertiary);}
.text-sm{font-size:var(--font-size-sm);}
.text-xs{font-size:var(--font-size-xs);}
.shell{
  max-width:1400px;margin:0 auto;padding:var(--space-5) var(--space-6) var(--space-6);
  display:flex;flex-direction:column;gap:var(--space-4);
}
.page-header{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);margin:var(--space-2) 0 var(--space-1);}
.section-header{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);margin:var(--space-4) 0 var(--space-3);}
.dashboard-grid{display:grid;grid-template-columns:1fr 360px;gap:var(--space-4);align-items:start;}
.dashboard-col{display:flex;flex-direction:column;gap:var(--space-3);}
.stat-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--space-3);}
.stat-tile{position:relative;overflow:hidden;padding:var(--space-3);}
.stat-tile .stat-value{font-family:var(--font-family-heading);font-size:var(--font-size-xl);font-weight:600;font-variant-numeric:tabular-nums;}
.stat-tile .stat-label{color:var(--color-text-tertiary);font-size:var(--font-size-xs);margin-top:var(--space-1);display:block;}
.stat-icon-badge{width:28px;height:28px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.panel-title{font-size:var(--font-size-md);font-weight:600;}
.active-matters-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--space-2);}
.active-matter-row{display:flex;flex-direction:column;gap:var(--space-2);padding:var(--space-3);}
.active-matter-card-title{font-size:var(--font-size-sm);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.active-matter-subtext{font-size:var(--font-size-xs);color:var(--color-text-tertiary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.matter-avatar{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--font-size-xs);font-weight:600;background:var(--color-primary-100);color:var(--color-primary-700);flex-shrink:0;}
.matter-avatar-xs{width:18px;height:18px;font-size:8px;}
.cal-strip{display:flex;gap:var(--space-2);}
.cal-day-cell{
  display:flex;flex:0 0 44px;flex-direction:column;align-items:center;gap:3px;padding:6px var(--space-1);
  border-radius:var(--radius-md);background:var(--color-bg-surface-sunken);border:1px solid transparent;min-height:56px;
}
.cal-day-today{border-color:var(--color-primary-500);background:var(--color-bg-selected);}
.cal-day-label{font-size:var(--font-size-xs);color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:0.04em;}
.cal-day-number{font-family:var(--font-family-heading);font-weight:600;font-size:var(--font-size-md);}
.cal-initial-badge{min-width:20px;height:18px;padding:0 4px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;background:var(--color-primary-100);color:var(--color-primary-700);}
.recent-row{display:flex;align-items:center;gap:var(--space-2);padding:6px var(--space-3);border-top:1px solid transparent;}
.recent-row + .recent-row{border-top-color:var(--color-neutral-100);}
.recent-title{flex:1;min-width:0;font-size:var(--font-size-sm);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.recent-meta{font-size:11px;color:var(--color-text-tertiary);flex-shrink:0;}
.breadcrumb{font-size:var(--font-size-xs);color:var(--color-text-tertiary);margin-bottom:var(--space-3);}
.tabs{display:flex;gap:var(--space-5);border-bottom:1px solid var(--color-neutral-200);margin-top:var(--space-4);}
.tab{
  display:inline-flex;align-items:center;gap:var(--space-2);padding:var(--space-3) var(--space-1);margin-bottom:-1px;
  border:none;background:none;border-bottom:2px solid transparent;font-family:var(--font-family-ui);
  font-size:var(--font-size-sm);color:var(--color-neutral-600);
}
.tab-active{color:var(--color-brand-700);font-weight:var(--font-weight-medium);border-bottom-color:var(--color-brand-600);}
.documents-columns{display:grid;grid-template-columns:1fr 300px;gap:var(--space-5);}
.panel-list-row{display:flex;align-items:center;gap:var(--space-2);padding:var(--space-2) 0;border-bottom:1px solid var(--color-border-default);}
.panel-list-row:last-child{border-bottom:none;}
.panel-list-row-text{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--font-size-sm);}
.panel-file-icon{flex-shrink:0;color:var(--color-text-tertiary);}
.ask-ai-btn{
  display:inline-flex;align-items:center;gap:var(--space-2);height:32px;padding:0 var(--space-3);
  border-radius:var(--radius-md);border:1px solid var(--color-ai-200);background:var(--color-ai-50);
  color:var(--color-ai-700);font-family:var(--font-family-ui);font-size:var(--font-size-xs);font-weight:var(--font-weight-medium);
}
.dropzone{
  border:1px dashed var(--color-neutral-300);border-radius:var(--radius-lg);background:var(--color-neutral-50);
  padding:var(--space-5) var(--space-4);display:flex;flex-direction:column;align-items:center;gap:var(--space-2);text-align:center;color:var(--color-text-tertiary);
}
.dropzone-title{font-size:var(--font-size-sm);color:var(--color-text-secondary);}
.dropzone-hint{font-size:var(--font-size-xs);}
.chat-msg{display:flex;gap:var(--space-3);padding:var(--space-4);border:1px solid var(--color-ai-200);background:var(--color-ai-50);border-radius:var(--radius-lg);}
.chat-avatar{width:26px;height:26px;border-radius:50%;background:var(--color-ai-500);color:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.chat-body{font-size:var(--font-size-sm);line-height:1.55;color:var(--color-neutral-800);}
.citation{
  display:inline-flex;align-items:center;gap:6px;margin-top:var(--space-3);padding:3px var(--space-2);
  border-radius:var(--radius-sm);background:var(--color-citation-50);border:1px solid var(--color-citation-200);
  color:var(--color-citation-500);font-family:var(--font-family-mono);font-size:var(--font-size-xs);
}
.field-label{font-size:var(--font-size-sm);font-weight:var(--font-weight-medium);color:var(--color-text-secondary);}
.client-dl{margin:var(--space-4) 0 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:var(--space-4);}
.client-dl dt{margin-bottom:var(--space-1);}
.client-dl dd{margin:0;font-size:var(--font-size-sm);color:var(--color-text-primary);}
.client-matter-row{display:flex;align-items:center;gap:var(--space-2);padding:var(--space-4);border-top:1px solid var(--color-neutral-200);}
.client-matter-row:last-child{border-bottom:1px solid var(--color-neutral-200);}
.client-matter-title{flex:1;min-width:0;font-weight:500;font-size:var(--font-size-sm);}
.icon-btn{width:28px;height:28px;border-radius:var(--radius-md);border:none;background:none;color:var(--color-text-tertiary);display:inline-flex;align-items:center;justify-content:center;}
`;

/* ------------------------------------------------------------------ *
 * The five type systems. Each supplies a Google Fonts @import and a
 * CSS override block. Palette / spacing / radius are never touched.
 * ------------------------------------------------------------------ */
const SYSTEMS = [
  {
    key: "Chambers",
    label: "Option A — Chambers",
    blurb: "Traditional legal authority",
    display: "Source Serif 4",
    text: "Public Sans",
    mono: "JetBrains Mono",
    import:
      "@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Public+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');",
    css: `
:root{
  --font-family-ui:'Public Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-heading:'Source Serif 4','Iowan Old Style','Palatino Linotype','Palatino',Georgia,'Times New Roman',serif;
  --font-family-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
h1,h2,h3,.panel-title,.app-nav-brand{font-family:var(--font-family-heading);letter-spacing:-0.006em;}
h1{font-weight:700;}
h2,h3,.panel-title{font-weight:600;}
.app-nav-brand{font-weight:700;letter-spacing:-0.01em;}
.field-label,.cal-day-label{text-transform:uppercase;letter-spacing:0.08em;font-size:11px;font-weight:600;color:var(--color-neutral-500);}
.breadcrumb,.recent-meta,.mono,code{font-variant-numeric:tabular-nums;}
.stat-tile .stat-value{font-weight:700;letter-spacing:-0.01em;}
`,
  },
  {
    key: "Statute",
    label: "Option B — Statute",
    blurb: "Institutional / government-register",
    display: "IBM Plex Serif",
    text: "IBM Plex Sans",
    mono: "IBM Plex Mono",
    import:
      "@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');",
    css: `
:root{
  --font-family-ui:'IBM Plex Sans','Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-heading:'IBM Plex Sans','Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{font-variant-numeric:tabular-nums;}
h1,.app-nav-brand{font-family:'IBM Plex Serif','Georgia',serif;font-weight:600;letter-spacing:-0.004em;}
h2,h3,.panel-title{font-weight:600;letter-spacing:0;}
.app-nav-brand{font-weight:600;}
.field-label,.cal-day-label{text-transform:uppercase;letter-spacing:0.10em;font-size:11px;font-weight:600;color:var(--color-neutral-500);}
.type-band,.breadcrumb{letter-spacing:0.06em;}
.stat-tile .stat-value{font-family:'IBM Plex Serif',Georgia,serif;font-weight:600;}
`,
  },
  {
    key: "Counsel",
    label: "Option C — Counsel",
    blurb: "Editorial, law-review contrast",
    display: "Lora",
    text: "Public Sans",
    mono: "JetBrains Mono",
    import:
      "@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,500;0,600;0,700;1,500&family=Public+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');",
    css: `
:root{
  --font-family-ui:'Public Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-heading:'Lora','Georgia','Times New Roman',serif;
  --font-family-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
h1,h2,h3,.panel-title,.app-nav-brand{font-family:var(--font-family-heading);font-weight:600;letter-spacing:0;}
h1{font-weight:600;}
.app-nav-brand{font-weight:600;}
body,.chat-body,.panel-list-row-text,.client-dl dd{line-height:1.62;}
.field-label{font-family:'Lora',Georgia,serif;font-style:italic;font-weight:500;text-transform:none;letter-spacing:0;font-size:13px;color:var(--color-neutral-600);}
.cal-day-label{text-transform:uppercase;letter-spacing:0.06em;font-size:11px;color:var(--color-neutral-500);}
.text-tertiary,.active-matter-subtext,.recent-meta,.breadcrumb{color:var(--color-neutral-600);}
.stat-tile .stat-value{font-weight:600;}
`,
  },
  {
    key: "Ledger",
    label: "Option D — Ledger",
    blurb: "Data-dense, mono-forward legal-tech",
    display: "Archivo",
    text: "Archivo",
    mono: "JetBrains Mono",
    import:
      "@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');",
    css: `
:root{
  --font-family-ui:'Archivo','Helvetica Neue','Segoe UI',Arial,sans-serif;
  --font-family-heading:'Archivo','Helvetica Neue','Segoe UI',Arial,sans-serif;
  --font-family-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{font-variant-numeric:tabular-nums;}
h1,h2,h3,.panel-title{font-weight:700;letter-spacing:-0.025em;}
.app-nav-brand{font-weight:700;letter-spacing:-0.03em;}
.app-nav-link{letter-spacing:-0.01em;}
.field-label,.cal-day-label{font-family:var(--font-family-mono);text-transform:uppercase;letter-spacing:0.03em;font-size:11px;font-weight:500;color:var(--color-neutral-500);}
.badge,.status-dot-badge,.active-matter-subtext,.recent-meta,.breadcrumb,.cal-initial-badge,.matter-avatar,.matter-avatar-xs,.acct-avatar,.client-dl dd,.dropzone-hint{font-family:var(--font-family-mono);}
.stat-tile .stat-value{font-family:var(--font-family-mono);font-weight:600;letter-spacing:-0.02em;}
.client-matter-title,.recent-title{letter-spacing:-0.01em;}
`,
  },
  {
    key: "Brief",
    label: "Option E — Brief",
    blurb: "Public Sans, disciplined (one family, done right)",
    display: "Public Sans",
    text: "Public Sans",
    mono: "JetBrains Mono",
    import:
      "@import url('https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');",
    css: `
:root{
  --font-family-ui:'Public Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-heading:'Public Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --font-family-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{font-variant-numeric:tabular-nums;}
h1{font-weight:700;letter-spacing:-0.019em;}
h2,.panel-title{font-weight:600;letter-spacing:-0.012em;}
h3,.active-matter-card-title,.client-matter-title{font-weight:600;letter-spacing:-0.006em;}
.app-nav-brand{font-weight:700;letter-spacing:-0.018em;}
body,.chat-body,.panel-list-row-text{line-height:1.55;}
.field-label,.cal-day-label{text-transform:uppercase;letter-spacing:0.075em;font-size:11px;font-weight:600;color:var(--color-neutral-500);}
.breadcrumb{text-transform:uppercase;letter-spacing:0.07em;font-size:10px;font-weight:600;color:var(--color-neutral-500);}
.stat-tile .stat-value{font-weight:700;letter-spacing:-0.02em;}
`,
  },
];

/* ------------------------------------------------------------------ *
 * Icons (inline, stroke-based, 16-20px) — one consistent set.
 * ------------------------------------------------------------------ */
const I = {
  search: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>`,
  bell: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>`,
  matters: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3v5a1 1 0 0 0 1 1h5"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z"/><path d="M9 13h6M9 17h6"/></svg>`,
  deadlines: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="16" rx="2"/><path d="M3.5 9.5h17M8 3v3M16 3v3"/></svg>`,
  notifications: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>`,
  folder: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/></svg>`,
  sparkle: `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.5c.4 2.9 1.1 4.9 2.1 5.9s3 1.7 5.9 2.1c-2.9.4-4.9 1.1-5.9 2.1s-1.7 3-2.1 5.9c-.4-2.9-1.1-4.9-2.1-5.9S6.9 11 4 10.6c2.9-.4 4.9-1.1 5.9-2.1S11.6 5.4 12 2.5Z"/></svg>`,
  file: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="panel-file-icon"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/></svg>`,
  download: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>`,
  upload: `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/></svg>`,
  pencil: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`,
  trash: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/></svg>`,
  plus: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`,
};

/* ------------------------------------------------------------------ *
 * Fictional sample data (a small India-practice caseload).
 * ------------------------------------------------------------------ */
const NAV = (active) => `
<div class="app-nav">
  <div class="app-nav-brand">Legal AI Assistant</div>
  <div class="app-nav-links">
    <div class="app-nav-link${active === "d" ? " app-nav-link-active" : ""}">Dashboard</div>
    <div class="app-nav-link${active === "c" ? " app-nav-link-active" : ""}">Clients</div>
    <div class="app-nav-link${active === "m" ? " app-nav-link-active" : ""}">Matters</div>
  </div>
  <div class="app-nav-search"><span class="app-nav-search-icon">${I.search}</span><input class="app-nav-search-input" placeholder="Search Clients &amp; Matters…" readonly></div>
  <div class="app-nav-actions">${I.bell}<span class="acct-avatar">PN</span></div>
</div>`;

const BAND = (s) => `
<div class="type-band">
  <b>${s.label}</b><span>|</span>Display&nbsp;·&nbsp;${s.display}<span>/</span>Text&nbsp;·&nbsp;${s.text}<span>/</span>Mono&nbsp;·&nbsp;${s.mono}
</div>`;

function statTile(icon, tone, value, label) {
  const tones = {
    primary: ["var(--color-primary-50)", "var(--color-primary-500)"],
    warning: ["var(--color-warning-bg)", "var(--color-warning-base)"],
    info: ["var(--color-info-bg)", "var(--color-info-base)"],
  };
  const [bg, fg] = tones[tone];
  return `<div class="card stat-tile">
    <div class="row-between" style="align-items:flex-start">
      <div class="stat-value">${value}</div>
      <div class="stat-icon-badge" style="background:${bg};color:${fg}">${I[icon]}</div>
    </div>
    <span class="stat-label">${label}</span>
  </div>`;
}

function activeMatter(av, title, sub, status) {
  const badge =
    status === "open"
      ? `<span class="status-dot-badge"><span class="status-dot status-dot-open"></span>Open</span>`
      : `<span class="status-dot-badge"><span class="status-dot status-dot-closed"></span>Closed</span>`;
  return `<div class="card active-matter-row">
    <div class="row-between"><span style="color:var(--color-text-tertiary)">${I.folder}</span>${badge}</div>
    <div class="row" style="gap:8px"><span class="matter-avatar">${av}</span><span class="active-matter-card-title">${title}</span></div>
    <div class="active-matter-subtext">${sub}</div>
  </div>`;
}

function calDay(lbl, num, tag, today) {
  return `<div class="cal-day-cell${today ? " cal-day-today" : ""}">
    <span class="cal-day-label">${lbl}</span>
    <span class="cal-day-number">${num}</span>
    ${tag ? `<span class="cal-initial-badge">${tag}</span>` : `<span style="height:18px"></span>`}
  </div>`;
}

function recentRow(av, title, meta) {
  return `<div class="recent-row">
    <span class="matter-avatar matter-avatar-xs">${av}</span>
    <span class="recent-title">${title}</span>
    <span class="recent-meta mono">${meta}</span>
  </div>`;
}

/* ---------------------------- SCREENS ---------------------------- */
function dashboard(s) {
  return `${BAND(s)}${NAV("d")}
<div class="shell">
  <div class="page-header">
    <h1 style="font-size:var(--font-size-2xl)">Dashboard</h1>
    <div class="row">
      <div class="btn btn-secondary btn-plain">${I.plus} New Client</div>
      <div class="btn btn-primary">${I.plus} New Matter</div>
    </div>
  </div>
  <div class="dashboard-grid">
    <div class="dashboard-col">
      <div class="stat-row">
        ${statTile("matters", "primary", "7", "Open Matters")}
        ${statTile("deadlines", "warning", "3", "Deadlines this week")}
        ${statTile("notifications", "info", "2", "Unread notifications")}
      </div>
      <div class="card" style="padding:var(--space-4)">
        <div class="row-between" style="margin-bottom:var(--space-3)">
          <span class="panel-title">Active Matters</span>
          <span class="text-tertiary text-xs">Sorted by next deadline</span>
        </div>
        <div class="active-matters-grid">
          ${activeMatter("ML", "Meridian — Warehouse Lease Renewal", "Meridian Logistics · Due Apr 12", "open")}
          ${activeMatter("AT", "Apex Textiles — GST Dispute (FY22)", "Apex Textiles · Due Apr 18", "open")}
          ${activeMatter("SD", "Sunrise Developers — RERA Review", "Sunrise Developers LLP · Due Apr 22", "open")}
          ${activeMatter("RD", "Rao v. Deshmukh — Partition Suit", "Grishma Rao · Due May 04", "open")}
          ${activeMatter("ML", "Meridian — Vendor MSA Redraft", "Meridian Logistics · Due May 09", "open")}
          ${activeMatter("KE", "Kaveri Estates — Title Due Diligence", "Kaveri Estates · Due May 15", "open")}
        </div>
      </div>
    </div>
    <div class="dashboard-col">
      <div class="card" style="padding:var(--space-4)">
        <div class="row-between" style="margin-bottom:var(--space-3)">
          <span class="panel-title">April 2026</span>
          <span class="text-tertiary text-xs">This week</span>
        </div>
        <div class="cal-strip">
          ${calDay("Mon", "6", "", false)}
          ${calDay("Tue", "7", "", false)}
          ${calDay("Wed", "8", "MSA", false)}
          ${calDay("Thu", "9", "", true)}
          ${calDay("Fri", "10", "", false)}
          ${calDay("Sat", "11", "", false)}
          ${calDay("Sun", "12", "WL", false)}
        </div>
      </div>
      <div class="card" style="padding:var(--space-4)">
        <div class="row-between" style="margin-bottom:var(--space-2)">
          <span class="panel-title">Recent Matters</span>
          <span class="text-tertiary text-xs">See all</span>
        </div>
        ${recentRow("AT", "Apex Textiles — GST Dispute (FY22)", "Apr 18")}
        ${recentRow("ML", "Meridian — Warehouse Lease Renewal", "Apr 12")}
        ${recentRow("RD", "Rao v. Deshmukh — Partition Suit", "May 04")}
        ${recentRow("SD", "Sunrise Developers — RERA Review", "Apr 22")}
        ${recentRow("KE", "Kaveri Estates — Title Due Diligence", "May 15")}
      </div>
    </div>
  </div>
</div>`;
}

function matter(s) {
  return `${BAND(s)}${NAV("m")}
<div class="shell">
  <div class="breadcrumb mono">Matters / Meridian — Warehouse Lease Renewal</div>
  <div class="page-header">
    <h1 style="font-size:var(--font-size-2xl)">Meridian — Warehouse Lease Renewal</h1>
    <div class="row" style="gap:var(--space-2)">
      <span class="status-dot-badge"><span class="status-dot status-dot-open"></span>Open</span>
      <div class="btn btn-secondary btn-sm">${I.trash} Delete</div>
    </div>
  </div>
  <div class="text-tertiary text-sm">Client: <a>Meridian Logistics Pvt Ltd</a></div>
  <div class="tabs">
    <div class="tab tab-active">Documents</div>
    <div class="tab">Chat</div>
    <div class="tab">Deadlines</div>
  </div>

  <div style="display:flex;flex-direction:column;gap:var(--space-5);margin-top:var(--space-4)">
    <section>
      <div class="documents-columns">
        <div>
          <div class="section-header">
            <h2 style="font-size:var(--font-size-lg)">Documents</h2>
            <div class="row" style="gap:var(--space-2)">
              <div class="ask-ai-btn">${I.sparkle} Ask AI</div>
            </div>
          </div>
          <div class="stack" style="gap:0">
            <div class="panel-list-row"><span style="color:var(--color-text-tertiary)">${I.download}</span><span style="color:var(--color-text-tertiary)">${I.file}</span><span class="panel-list-row-text">Warehouse_Lease_2019.pdf</span></div>
            <div class="panel-list-row"><span style="color:var(--color-text-tertiary)">${I.download}</span><span style="color:var(--color-text-tertiary)">${I.file}</span><span class="panel-list-row-text">Lease_Amendment_Draft_v3.docx</span><span class="badge badge-warning">Draft</span></div>
            <div class="panel-list-row"><span style="color:var(--color-text-tertiary)">${I.download}</span><span style="color:var(--color-text-tertiary)">${I.file}</span><span class="panel-list-row-text">Title_Deed_Meridian.pdf</span></div>
            <div class="panel-list-row"><span style="color:var(--color-text-tertiary)">${I.download}</span><span style="color:var(--color-text-tertiary)">${I.file}</span><span class="panel-list-row-text">Rent_Schedule_2024.xlsx</span><span class="text-tertiary text-xs">processing</span></div>
          </div>

          <div class="chat-msg" style="margin-top:var(--space-4)">
            <span class="chat-avatar">${I.sparkle}</span>
            <div class="chat-body">
              <span class="badge badge-ai" style="margin-bottom:6px">AI answer</span>
              <p>The renewal term runs <b>36 months</b> from 1 April 2025, with a single 24-month extension option exercisable on 90 days' written notice (clause 4.2). Rent escalates 5% annually.</p>
              <span class="citation">${I.file} Warehouse_Lease_2019.pdf · p.4 · §4.2</span>
            </div>
          </div>
        </div>
        <div>
          <div class="dropzone">
            ${I.upload}
            <div class="dropzone-title">Drag and drop or</div>
            <div class="dropzone-hint">PDF, DOCX, PNG, JPG, TIFF, WEBP</div>
            <div class="btn btn-secondary btn-sm" style="margin-top:var(--space-2)">Upload File</div>
          </div>
        </div>
      </div>
    </section>

    <section style="max-width:65%">
      <div class="section-header">
        <h2 style="font-size:var(--font-size-lg)">Deadlines</h2>
        <div class="btn btn-secondary btn-sm">${I.plus} New Deadline</div>
      </div>
      <div class="stack" style="gap:0">
        <label class="panel-list-row"><input type="checkbox" checked disabled><span class="panel-list-row-text" style="text-decoration:line-through">Serve renewal notice on landlord</span><span class="text-xs mono text-tertiary">Mar 28</span></label>
        <label class="panel-list-row"><input type="checkbox" disabled><span class="panel-list-row-text">File lease amendment with registrar</span><span class="text-xs mono" style="color:var(--color-error-text)">Apr 12</span></label>
        <label class="panel-list-row"><input type="checkbox" disabled><span class="panel-list-row-text">Board resolution circulation <span style="color:var(--color-warning-text)">· Critical</span></span><span class="text-xs mono text-tertiary">Apr 22</span></label>
      </div>
      <div style="margin-top:var(--space-4)"><div class="btn btn-secondary btn-sm">Close Matter</div></div>
    </section>
  </div>
</div>`;
}

function client(s) {
  const row = (title, due, status) => {
    const badge =
      status === "open"
        ? `<span class="status-dot-badge"><span class="status-dot status-dot-open"></span>Open</span>`
        : `<span class="status-dot-badge"><span class="status-dot status-dot-closed"></span>Closed</span>`;
    return `<div class="client-matter-row">
      <span class="client-matter-title">${title}</span>
      <div class="row" style="gap:var(--space-3)">
        ${due ? `<span class="text-tertiary text-sm mono">Due ${due}</span>` : ""}
        ${badge}
      </div>
      <button class="icon-btn">${I.trash}</button>
    </div>`;
  };
  return `${BAND(s)}${NAV("c")}
<div class="shell">
  <div class="breadcrumb mono">Clients / Meridian Logistics Pvt Ltd</div>
  <div class="page-header">
    <h1 style="font-size:var(--font-size-2xl)">Meridian Logistics Pvt Ltd</h1>
    <div class="row" style="gap:var(--space-1)">
      <button class="icon-btn">${I.pencil}</button>
      <button class="icon-btn">${I.trash}</button>
    </div>
  </div>

  <dl class="client-dl">
    <div><dt class="field-label">Contact email</dt><dd>ops@meridianlogistics.in</dd></div>
    <div><dt class="field-label">Contact phone</dt><dd>+91 22 4002 1188</dd></div>
    <div><dt class="field-label">Added</dt><dd>March 3, 2026</dd></div>
    <div style="grid-column:1 / -1"><dt class="field-label">Notes</dt><dd>Prefers email over calls. GST and indirect-tax matters routed to Adv. Kulkarni. Renewal cycle for the Bhiwandi warehouse falls every April.</dd></div>
  </dl>

  <div class="row" style="gap:var(--space-2);margin:var(--space-5) 0 var(--space-2)">
    <h2 style="font-size:var(--font-size-xl)">Matters</h2>
    <button class="icon-btn">${I.plus}</button>
  </div>
  <div>
    ${row("Meridian — Warehouse Lease Renewal", "Apr 12", "open")}
    ${row("Meridian — Vendor MSA Redraft", "May 09", "open")}
    ${row("Meridian — Customs Penalty Appeal", "", "closed")}
    ${row("Meridian — Employment Policy Refresh", "", "closed")}
  </div>
</div>`;
}

/* ------------------------------------------------------------------ *
 * Assemble .dc.html files + canvas.json
 * ------------------------------------------------------------------ */
function dcFile(title, styleBody, markup) {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <style>
${styleBody}
  </style>
</helmet>
<div class="artboard-root">
${markup}
</div>
</x-dc>
</body>
</html>
`;
}

const SCREENS = [
  { slug: "Dashboard", fn: dashboard, col: 0 },
  { slug: "Matter", fn: matter, col: 1 },
  { slug: "Client", fn: client, col: 2 },
];

const W = 1480;
const H = 1180;
const GAP_X = 160;
const GAP_Y = 200;
const colX = [0, W + GAP_X, 2 * (W + GAP_X)];

const SYS_NOTES = {
  Chambers:
    "Serif page titles and section heads read as a printed brief; the sans body keeps forms and dense lists calm. Micro-labels go small-caps. Reuses Source Serif 4, already bundled in the app but currently unused.",
  Statute:
    "One superfamily (IBM Plex) across sans, serif and mono, so headings, body and citation refs feel cut from the same block. Tabular figures everywhere; a Plex Serif H1 gives each page a gazette-like nameplate.",
  Counsel:
    "High contrast between a warm bookish serif (Lora) for headings and a plain sans body, with a longer line-height for reading. Field labels are set in serif italic — a law-review register rather than a SaaS one.",
  Ledger:
    "Grotesque UI (Archivo) with tight tracking, and JetBrains Mono pushed forward onto every number, badge, date, ID and avatar. Reads like a legal-tech terminal — best if the product leans data-heavy.",
  Brief:
    "Keeps the current single family (Public Sans) but rebuilds the hierarchy: real weight steps, negative tracking on display sizes, tracked upper-case eyebrows, tabular numerals. The 'the usage was the problem, not the font' option — zero new webfonts.",
};

const artboards = [];
const annotations = [];
const files = {};

SYSTEMS.forEach((s, r) => {
  const y = r * (H + GAP_Y);
  const rootStyle = `
.artboard-root{width:${W}px;min-height:${H}px;background:linear-gradient(to left,#FFFFFF,var(--color-bg-page));overflow:hidden;}
`;
  SCREENS.forEach((sc) => {
    const isMain = r === 0 && sc.col === 0;
    const name = isMain ? "Main.dc.html" : `${s.key}${sc.slug}.dc.html`;
    const style = [s.import, BASE_CSS, s.css, rootStyle].join("\n");
    files[name] = dcFile(`${s.label} — ${sc.slug}`, style, sc.fn(s));
    artboards.push({ file: name, x: colX[sc.col], y, w: W, h: H });
  });
  annotations.push({
    id: `sys-${s.key.toLowerCase()}`,
    x: -720,
    y: y + 40,
    w: 600,
    text: `${s.label}  —  ${s.blurb}\n\nDisplay / headings:  ${s.display}\nBody / UI text:  ${s.text}\nCitations · IDs · dates:  ${s.mono}\n\n${SYS_NOTES[s.key]}`,
  });
});

annotations.push({
  id: "how-to-read",
  x: -720,
  y: -150,
  w: 600,
  text:
    "TYPOGRAPHY DIRECTIONS — Legal AI Assistant\n\nRows = five type systems. Columns = Dashboard, Matter, Client.\nLayout, colour palette, spacing, radii and the page background are identical in every row — only the typeface, weights, size ramp, letter-spacing, casing and mono usage change. Pick a row and I'll wire it into globals.css.",
});

const canvas = {
  artboards,
  annotations,
  launch: { view: "canvas" },
};
files["canvas.json"] = JSON.stringify(canvas, null, 2);

for (const [name, content] of Object.entries(files)) {
  writeFileSync(join(OUT, name), content);
}
console.log(`wrote ${Object.keys(files).length} files to ${OUT}`);
console.log(Object.keys(files).join("\n"));
