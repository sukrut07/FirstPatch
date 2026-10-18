"use client";

import { useState, useEffect, useMemo } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import { 
  BarChart3, 
  PieChart as PieIcon, 
  Radar as RadarIcon, 
  CheckCircle2, 
  ShieldCheck, 
  Code2, 
  FileCode, 
  Cpu
} from "lucide-react";

interface CodebaseDiagramsProps {
  files: any[];
  arch: any;
  issues: any[];
  repoData: any;
}

const PALETTE = [
  "#10b981", // Emerald
  "#06b6d4", // Cyan
  "#8b5cf6", // Purple
  "#f59e0b", // Amber
  "#ec4899", // Pink
  "#3b82f6", // Blue
  "#64748b", // Slate
];

export default function CodebaseDiagrams({ files, arch, issues, repoData }: CodebaseDiagramsProps) {
  const [mounted, setMounted] = useState(false);
  const [selectedIssueIdx, setSelectedIssueIdx] = useState(0);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 1. File Type / Language Composition Data
  const fileTypeData = useMemo(() => {
    const map: Record<string, { count: number; bytes: number }> = {};
    (files || []).forEach((f) => {
      const ext = f.path.includes(".") ? f.path.split(".").pop()!.toLowerCase() : "other";
      if (!map[ext]) map[ext] = { count: 0, bytes: 0 };
      map[ext].count += 1;
      map[ext].bytes += f.size_bytes || 0;
    });

    return Object.entries(map)
      .map(([ext, val]) => ({
        name: `.${ext}`,
        count: val.count,
        kb: Math.round((val.bytes / 1024) * 10) / 10,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 6);
  }, [files]);

  // 2. AST Symbol Density by Module (Functions, Classes, Tests)
  const moduleDensityData = useMemo(() => {
    const modules = arch?.modules || [];
    return modules
      .map((m: any) => {
        const basename = m.path.split("/").pop() || m.path;
        return {
          name: basename.length > 18 ? basename.slice(0, 16) + "..." : basename,
          fullPath: m.path,
          functions: (m.functions || []).length,
          classes: (m.classes || []).length,
          isTest: m.is_test ? 1 : 0,
        };
      })
      .sort((a: any, b: any) => b.functions + b.classes - (a.functions + a.classes))
      .slice(0, 8);
  }, [arch]);

  // 3. Multi-Dimensional Issue Fit Radar Data
  const radarData = useMemo(() => {
    if (!issues || issues.length === 0) {
      return [
        { metric: "Technical Fit", score: 85, fullMark: 100 },
        { metric: "Interest Match", score: 90, fullMark: 100 },
        { metric: "Evidence Depth", score: 80, fullMark: 100 },
        { metric: "Solvability", score: 75, fullMark: 100 },
        { metric: "Learning Value", score: 95, fullMark: 100 },
      ];
    }

    const currentIssue = issues[selectedIssueIdx] || issues[0];
    return [
      { metric: "Technical Fit", score: currentIssue.technical_fit_score || 85, fullMark: 100 },
      { metric: "Interest Match", score: currentIssue.interest_fit_score || 80, fullMark: 100 },
      { metric: "Evidence Depth", score: currentIssue.evidence_confidence_score || 78, fullMark: 100 },
      { metric: "Solvability", score: currentIssue.viability_score || 72, fullMark: 100 },
      { metric: "Learning Value", score: currentIssue.learning_value_score || 90, fullMark: 100 },
    ];
  }, [issues, selectedIssueIdx]);

  // 4. Test vs Implementation Ratio
  const testRatioData = useMemo(() => {
    let testCount = 0;
    let sourceCount = 0;
    let configCount = 0;

    (files || []).forEach((f) => {
      if (f.is_test) testCount++;
      else if (f.is_config) configCount++;
      else sourceCount++;
    });

    return [
      { name: "Source Code", value: sourceCount, color: "#10b981" },
      { name: "Test Suites", value: testCount, color: "#06b6d4" },
      { name: "Configs & Meta", value: configCount, color: "#f59e0b" },
    ];
  }, [files]);

  if (!mounted) {
    return (
      <div className="flex items-center justify-center p-12 text-zinc-500 text-xs font-mono">
        Loading Codebase Visual Analysis Charts...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Indexed Files</span>
            <FileCode className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">{files?.length || 0}</div>
          <p className="text-[11px] text-zinc-500 font-mono">AST parsed snapshot</p>
        </div>

        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Discovered Modules</span>
            <Cpu className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">{arch?.modules_count || 0}</div>
          <p className="text-[11px] text-zinc-500 font-mono">Structural boundaries</p>
        </div>

        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Test Suite Files</span>
            <CheckCircle2 className="h-4 w-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">{(arch?.test_suite || []).length}</div>
          <p className="text-[11px] text-zinc-500 font-mono">Automated verification</p>
        </div>

        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Scored Issues</span>
            <ShieldCheck className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">{issues?.length || 0}</div>
          <p className="text-[11px] text-zinc-500 font-mono">Multi-dimensional fit</p>
        </div>
      </div>

      {/* Grid of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CHART 1: Language & Extension Distribution */}
        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PieIcon className="h-4 w-4 text-emerald-400" />
              <h3 className="text-xs font-semibold text-zinc-200">
                File Type & Language Distribution
              </h3>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">By file extension count</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={fileTypeData}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={45}
                  paddingAngle={4}
                  label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                >
                  {fileTypeData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#e4e4e7",
                  }}
                  formatter={(value: any, name: any, item: any) => [
                    `${value} files (${item.payload.kb} KB)`,
                    item.payload.name,
                  ]}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  wrapperStyle={{ fontSize: "11px", color: "#a1a1aa" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            Breakdown of source files, config manifests, and test modules indexed in the current repository snapshot.
          </p>
        </div>

        {/* CHART 2: AST Symbol Breakdown (Functions vs Classes) */}
        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-cyan-400" />
              <h3 className="text-xs font-semibold text-zinc-200">
                AST Symbol Density by Module
              </h3>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">Top source files</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={moduleDensityData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis
                  dataKey="name"
                  stroke="#71717a"
                  fontSize={10}
                  angle={-20}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis stroke="#71717a" fontSize={10} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#e4e4e7",
                  }}
                />
                <Legend
                  verticalAlign="top"
                  height={30}
                  iconType="circle"
                  wrapperStyle={{ fontSize: "11px", color: "#a1a1aa" }}
                />
                <Bar dataKey="functions" name="Functions" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                <Bar dataKey="classes" name="Classes" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            Measures code complexity and modularity. High function density pinpoints core implementation engines.
          </p>
        </div>

        {/* CHART 3: Issue Multi-Dimensional Fit Radar */}
        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RadarIcon className="h-4 w-4 text-emerald-400" />
              <h3 className="text-xs font-semibold text-zinc-200">
                Issue Multi-Dimensional Fit Profile
              </h3>
            </div>
            {issues?.length > 0 && (
              <select
                value={selectedIssueIdx}
                onChange={(e) => setSelectedIssueIdx(Number(e.target.value))}
                className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-[11px] rounded px-2 py-1 focus:outline-none focus:border-emerald-500"
              >
                {issues.map((iss, i) => (
                  <option key={iss.id || i} value={i}>
                    #{iss.number} - {(iss.title || "").slice(0, 24)}...
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius={75} data={radarData}>
                <PolarGrid stroke="#27272a" />
                <PolarAngleAxis dataKey="metric" stroke="#a1a1aa" fontSize={10} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#52525b" fontSize={9} />
                <Radar
                  name="Fit Score (0-100)"
                  dataKey="score"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.35}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#e4e4e7",
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            Evaluates beginner suitability across Technical Depth, Contributor Interests, Evidence Strength, Solvability, and Learning Opportunities.
          </p>
        </div>

        {/* CHART 4: Code vs Test vs Config Architecture Breakdown */}
        <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Code2 className="h-4 w-4 text-amber-400" />
              <h3 className="text-xs font-semibold text-zinc-200">
                Architecture Composition & Test Ratio
              </h3>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">Safety & Test coverage</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={testRatioData}
                layout="vertical"
                margin={{ top: 15, right: 30, left: 30, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                <XAxis type="number" stroke="#71717a" fontSize={10} />
                <YAxis dataKey="name" type="category" stroke="#71717a" fontSize={11} width={80} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#e4e4e7",
                  }}
                  formatter={(val: any) => [`${val} files`, "Count"]}
                />
                <Bar dataKey="value" name="File Count" radius={[0, 4, 4, 0]}>
                  {testRatioData.map((entry, index) => (
                    <Cell key={`ratio-cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            A balanced test suite gives beginners confidence when modifying unfamiliar code.
          </p>
        </div>
      </div>
    </div>
  );
}
