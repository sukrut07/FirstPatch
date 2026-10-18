"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listContributions } from "@/lib/api";
import { 
  GitPullRequest, 
  ArrowRight, 
  Clock, 
  CheckCircle2, 
  Layers, 
  Calendar,
  Plus
} from "lucide-react";

export default function ContributionsListPage() {
  const [contributions, setContributions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listContributions().then((list) => {
      setContributions(list);
      setLoading(false);
    });
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-1.5">
            <GitPullRequest className="h-3 w-3" />
            <span>Flight Recorder Journeys</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">Contribution Workspaces</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Track your progress across open-source issues, verify local test outputs, and generate review-ready pull requests.
          </p>
        </div>

        <Link
          href="/explore"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer shrink-0"
        >
          <Plus className="h-3.5 w-3.5" />
          Start New Contribution
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-20 text-xs text-zinc-500">Loading contribution workspaces...</div>
      ) : contributions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-800 p-12 text-center bg-zinc-900/20 space-y-3">
          <GitPullRequest className="h-10 w-10 text-zinc-600 mx-auto" />
          <h3 className="text-sm font-semibold text-zinc-200">No contribution workspaces yet.</h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto">
            Explore an analyzed repository, pick a candidate issue, and start your first guided contribution plan.
          </p>
          <Link
            href="/explore"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-medium transition-colors"
          >
            Explore Repositories <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {contributions.map((c) => {
            const progress = c.total_steps > 0 ? Math.round((c.completed_steps / c.total_steps) * 100) : 0;
            return (
              <Link
                key={c.id}
                href={`/contributions/${c.id}`}
                className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-mono text-xs text-emerald-400 font-semibold truncate">
                      {c.repository_id}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {c.status}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-zinc-200 group-hover:text-emerald-400 transition-colors mb-2 line-clamp-1">
                    {c.title}
                  </h3>
                  <p className="text-xs text-zinc-400 line-clamp-2 mb-4">
                    {c.description || "Guided open-source contribution plan."}
                  </p>
                </div>

                <div className="space-y-2 border-t border-zinc-800/80 pt-3">
                  <div className="flex justify-between text-[11px] text-zinc-400">
                    <span>Progress: {c.completed_steps}/{c.total_steps} steps</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
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
