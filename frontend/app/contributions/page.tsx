"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listContributions } from "@/lib/api";
import {
  GitPullRequest,
  CheckCircle2,
  Clock,
  ArrowRight,
  Folder,
  Plus,
  Compass,
  FileCode,
  ShieldCheck,
} from "lucide-react";

export default function ContributionsListPage() {
  const [contributions, setContributions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listContributions()
      .then((res) => {
        if (Array.isArray(res)) setContributions(res);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200/80 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-200/80 flex items-center justify-center text-purple-600 shadow-sm">
              <GitPullRequest className="w-4 h-4" />
            </span>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Flight Recorder Workspaces</h1>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Track active contribution journeys, test verification logs, and simulated maintainer reviews.
          </p>
        </div>

        <Link
          href="/explore"
          className="btn-primary text-xs py-2.5 px-4 shadow-md inline-flex items-center gap-1.5"
        >
          <Compass className="w-4 h-4" />
          Find New Issue
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 h-48 skeleton" />
          ))}
        </div>
      ) : contributions.length === 0 ? (
        <div className="card p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-3xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto shadow-sm">
            <GitPullRequest className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-gray-900">No Contribution Journeys Yet</h3>
          <p className="text-xs text-gray-500 max-w-md mx-auto">
            Choose a repository from Explore or Dashboard, investigate an issue, and generate an evidence-backed contribution workspace.
          </p>
          <Link
            href="/explore"
            className="btn-primary text-xs py-2.5 px-5 rounded-2xl inline-flex items-center gap-2"
          >
            <Compass className="w-4 h-4" />
            Browse Repositories
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {contributions.map((c) => {
            const steps = c.steps || [];
            const completedCount = steps.filter((s: any) => s.status === "completed").length;
            const progress = steps.length > 0 ? Math.round((completedCount / steps.length) * 100) : 0;

            return (
              <Link
                key={c.id}
                href={`/contributions/${c.id}`}
                className="card-hover p-6 flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="badge-brand font-mono text-[10px]">{c.repository_id}</span>
                    <span className="badge-success text-[10px] uppercase font-bold">
                      {c.status || "In Progress"}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors leading-snug">
                    {c.title}
                  </h3>
                  {c.description && (
                    <p className="text-xs text-gray-500 line-clamp-2 mt-1.5 leading-relaxed">
                      {c.description}
                    </p>
                  )}
                </div>

                <div className="mt-5 pt-4 border-t border-gray-100 space-y-2">
                  <div className="flex justify-between text-[11px] text-gray-500 font-semibold">
                    <span>Progress ({completedCount}/{steps.length || 4} steps)</span>
                    <span className="text-brand-600 font-mono font-bold">{progress}%</span>
                  </div>
                  <div className="score-bar">
                    <div
                      className="score-fill bg-gradient-to-r from-brand-500 to-purple-600"
                      style={{ width: `${Math.max(progress, 15)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs font-bold text-brand-600 pt-2">
                    <span>Open Flight Recorder</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
