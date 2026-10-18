import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    glossary: [
      { term: "Repository (Repo)", definition: "A folder managed by Git containing all project files, history, commits, and branches." },
      { term: "Fork", definition: "A personal copy of someone else's GitHub repository that lives on your account, allowing you to experiment freely without affecting the original project." },
      { term: "Branch", definition: "An independent line of development. Always create a new branch for your feature or bug fix instead of working on 'main'." },
      { term: "Clone", definition: "Downloading a complete copy of a remote GitHub repository to your local computer." },
      { term: "Upstream", definition: "The original open-source repository you forked from. Keeping your local branch synced with upstream prevents merge conflicts." },
      { term: "Commit", definition: "A recorded snapshot of your changes with an explanatory message describing what you modified and why." },
      { term: "Pull Request (PR)", definition: "A proposal submitted to the upstream project maintainers asking them to review and merge your changes into the main codebase." },
      { term: "Code Review", definition: "Maintainers reading your PR line-by-line, asking questions, requesting adjustments, and ensuring the change follows project conventions." },
      { term: "Continuous Integration (CI)", definition: "Automated pipelines that run linters and unit tests on every PR to verify that the change doesn't break existing functionality." },
      { term: "Virtual Environment", definition: "An isolated Python workspace that prevents package version conflicts between different projects on your computer." },
      { term: "Linter / Formatter", definition: "Tools (e.g. Ruff, Black, ESLint, Prettier) that automatically enforce consistent code formatting and flag syntax mistakes." },
      { term: "Regression", definition: "A bug that unintentionally breaks previously working functionality after a new change is introduced." },
      { term: "DCO / CLA", definition: "Developer Certificate of Origin (Signed-off-by) or Contributor License Agreement certifying that you have the right to contribute your code to the open-source project." }
    ]
  });
}
