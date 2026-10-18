import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    sequence: [
      { step: 1, title: "Discover Project", desc: "Identify a reputable, active project matching your interests." },
      { step: 2, title: "Read Project Overview", desc: "Understand the project mission, target audience, and main technologies." },
      { step: 3, title: "Understand Architecture", desc: "Explore the component diagram, entry points, and module responsibilities." },
      { step: 4, title: "Read CONTRIBUTING.md", desc: "Check project contribution rules, branch naming, and commit style." },
      { step: 5, title: "Find Suitable Issue", desc: "Choose an issue matching your skill level and available time." },
      { step: 6, title: "Check Claim-Safety", desc: "Verify that no other contributor is already actively working on the task." },
      { step: 7, title: "Fork Repository", desc: "Create a personal GitHub copy of the project to stage your work." },
      { step: 8, title: "Create Working Branch", desc: "Create a dedicated Git branch (e.g., `fix/config-keyerror`)." },
      { step: 9, title: "Set Up Environment", desc: "Install dependencies in an isolated virtual environment." },
      { step: 10, title: "Map Affected Code", desc: "Locate exact functions and classes responsible for the issue." },
      { step: 11, title: "Design Minimal Fix", desc: "Plan the smallest clean change that resolves the bug." },
      { step: 12, title: "Implement Changes", desc: "Write code following project conventions and style." },
      { step: 13, title: "Add or Update Tests", desc: "Add regression unit tests in `tests/` covering your change." },
      { step: 14, title: "Run Verification Suite", desc: "Execute tests locally to ensure 100% pass rate." },
      { step: 15, title: "Review Diff", desc: "Audit git diff for accidental prints or credentials." },
      { step: 16, title: "Commit Changes", desc: "Write clear conventional commit messages." },
      { step: 17, title: "Open Pull Request", desc: "Submit PR linking the issue (`Fixes #123`) with test proof." },
      { step: 18, title: "Respond to Review", desc: "Politely address maintainer feedback until merged." }
    ]
  });
}
