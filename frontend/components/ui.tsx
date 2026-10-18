"use client";

import React from "react";

// ---------------------------------------------------------------------------
// Icons (inline SVG — no external icon deps)
// ---------------------------------------------------------------------------

export function IconGitHub({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
    </svg>
  );
}

export function IconSearch({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607z" />
    </svg>
  );
}

export function IconSpinner({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={`${className} animate-spin`} fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function IconCheck({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

export function IconX({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

export function IconWarning({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

export function IconInfo({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0zm-9-3.75h.008v.008H12V8.25z" />
    </svg>
  );
}

export function IconFolder({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v8.25m19.5 0H2.25a2.25 2.25 0 0 1-2.25-2.25V6m19.5 0A2.25 2.25 0 0 0 19.5 6h-3.19a1.5 1.5 0 0 0-1.06.44l-2.12 2.12" />
    </svg>
  );
}

export function IconStar({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5z" />
    </svg>
  );
}

export function IconBranch({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h-.75A2.25 2.25 0 0 0 4.5 9.75v7.5a2.25 2.25 0 0 0 2.25 2.25h7.5a2.25 2.25 0 0 0 2.25-2.25v-7.5a2.25 2.25 0 0 0-2.25-2.25h-.75m-6 3.75 3 3m0 0 3-3m-3 3V1.5m6 9h.75a2.25 2.25 0 0 1 2.25 2.25v7.5a2.25 2.25 0 0 1-2.25 2.25h-7.5a2.25 2.25 0 0 1-2.25-2.25v-.75" />
    </svg>
  );
}

export function IconExternal({ className = "w-3 h-3" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
    </svg>
  );
}

export function IconSparkle({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z"/>
    </svg>
  );
}

export function IconCursor({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M3.75 2.25a.75.75 0 0 0-.75.75v18a.75.75 0 0 0 1.28.53l5.05-5.05 4.22 8.44a.75.75 0 0 0 1.34-.67l-4.14-8.28h6.25a.75.75 0 0 0 .53-1.28L4.28 2.47a.75.75 0 0 0-.53-.22Z" />
    </svg>
  );
}

export function IconCode({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
    </svg>
  );
}

export function IconLayers({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m6.75 7.5 5.25 3 5.25-3-5.25-3-5.25 3Zm0 6 5.25 3 5.25-3m-10.5 3 5.25 3 5.25-3" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Reusable UI Components (light-mode)
// ---------------------------------------------------------------------------

/** Score bar showing normalized 0–1 score */
export function ScoreBar({ score, className = "" }: { score: number; className?: string }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? "from-brand-500 to-lavender-500" :
    pct >= 40 ? "from-amber-400 to-orange-400" :
    "from-red-400 to-rose-400";
  return (
    <div className={`score-bar ${className}`} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className={`score-fill bg-gradient-to-r ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Difficulty badge */
export function DifficultyBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    beginner:     "difficulty-beginner",
    intermediate: "difficulty-intermediate",
    advanced:     "difficulty-advanced",
    unknown:      "difficulty-unknown",
  };
  const labels: Record<string, string> = {
    beginner:     "Beginner",
    intermediate: "Intermediate",
    advanced:     "Advanced",
    unknown:      "Unknown",
  };
  return <span className={styles[level] ?? "badge-muted"}>{labels[level] ?? level}</span>;
}

/** Evidence status badge */
export function EvidenceBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    verified:    "evidence-verified",
    inferred:    "evidence-inferred",
    unavailable: "evidence-missing",
    stale:       "evidence-stale",
  };
  const labels: Record<string, string> = {
    verified:    "✓ Verified",
    inferred:    "~ Inferred",
    unavailable: "✗ Missing",
    stale:       "⏱ Stale",
  };
  return <span className={styles[status] ?? "badge-muted"}>{labels[status] ?? status}</span>;
}

/** Analysis status indicator */
export function StatusIndicator({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string; dot: string }> = {
    complete:    { color: "text-status-success", label: "Analysis complete",    dot: "bg-status-success" },
    partial:     { color: "text-status-warning", label: "Partial analysis",     dot: "bg-status-warning" },
    failed:      { color: "text-status-error",   label: "Analysis failed",      dot: "bg-status-error" },
    in_progress: { color: "text-status-info",    label: "Analyzing…",           dot: "bg-status-info animate-pulse" },
    pending:     { color: "text-gray-500",       label: "Pending",              dot: "bg-gray-400" },
  };
  const cfg = map[status] ?? { color: "text-gray-500", label: status, dot: "bg-gray-400" };
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

/** Loading skeleton */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton h-4 ${className}`} aria-hidden="true" />;
}

/** Empty state */
export function EmptyState({ title, description, action }: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center animate-in">
      <div className="w-20 h-20 rounded-3xl bg-lavender-100 border border-lavender-200 flex items-center justify-center mb-5 shadow-panel-inner-glow">
        <IconSearch className="w-9 h-9 text-brand-400" />
      </div>
      <h3 className="text-base font-bold text-gray-700 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 max-w-sm leading-relaxed">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/** Error state */
export function ErrorState({ title, message, onRetry }: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="notice-error animate-in" role="alert">
      <IconWarning className="w-4 h-4 shrink-0 mt-0.5" />
      <div>
        {title && <p className="font-semibold mb-1">{title}</p>}
        <p className="text-sm">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className="mt-2 btn-ghost text-xs py-1 px-2">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

/** External link that always opens in a new tab */
export function ExternalLink({ href, children, className = "" }: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 text-brand-600 hover:text-brand-800 transition-colors font-medium ${className}`}
    >
      {children}
      <IconExternal />
    </a>
  );
}

/** Label chip for GitHub issue labels */
export function IssueLabel({ name, color }: { name: string; color?: string }) {
  const bgColor  = color ? `#${color}20` : undefined;
  const textColor = color ? `#${color}` : undefined;
  return (
    <span
      className="badge text-xs"
      style={{ backgroundColor: bgColor, color: textColor, borderColor: color ? `#${color}40` : undefined }}
    >
      {name}
    </span>
  );
}

/** Stat card chip for repo stats */
export function StatChip({ icon, value, label }: { icon: React.ReactNode; value: string | number; label: string }) {
  return (
    <div className="stat-chip">
      <span className="text-brand-500">{icon}</span>
      <div>
        <p className="text-sm font-bold text-gray-800 leading-none">{value}</p>
        <p className="text-[10px] text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  );
}