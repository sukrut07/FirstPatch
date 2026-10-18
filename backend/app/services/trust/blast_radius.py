"""Blast-Radius and Change-Impact Analysis.

Traces direct imports, callers, and related test suites for a proposed file or symbol change.
Distinguishes high-confidence Python AST facts from lower-confidence structural regex fallbacks.
Produces deterministic impact summaries without inventing uncalibrated probability scores.
"""

import ast
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from app.services.trust.fact_store import normalize_repo_path


class ImpactItem(BaseModel):
    file_path: str
    impact_type: str  # "direct_import", "caller", "related_test", "interface"
    symbol_name: Optional[str] = None
    confidence: str = "high"  # "high" (AST), "medium", "low" (regex fallback)
    evidence_snippet: Optional[str] = None


class BlastRadiusReport(BaseModel):
    target_path: str
    target_symbol: Optional[str] = None
    affected_files_count: int
    direct_importers: List[str] = Field(default_factory=list)
    related_tests: List[str] = Field(default_factory=list)
    impact_items: List[ImpactItem] = Field(default_factory=list)
    parser_tier: str  # "python_ast_high_confidence", "structural_regex_low_confidence"
    qualitative_risk_note: str


class BlastRadiusAnalyzer:
    def analyze_impact(
        self,
        target_path: str,
        files_dict: Dict[str, str],
        target_symbol: Optional[str] = None,
    ) -> BlastRadiusReport:
        clean_target = normalize_repo_path(target_path)
        is_python = clean_target.endswith(".py")
        parser_tier = "python_ast_high_confidence" if is_python else "structural_regex_low_confidence"

        target_module_name = clean_target.replace("/", ".").rstrip(".py")
        if target_module_name.endswith(".__init__"):
            target_module_name = target_module_name[:-9]
        short_mod_name = clean_target.split("/")[-1].replace(".py", "")

        impact_items: List[ImpactItem] = []
        importers: Set[str] = set()
        tests: Set[str] = set()

        for path, content in files_dict.items():
            try:
                norm_p = normalize_repo_path(path)
            except ValueError:
                continue

            if norm_p == clean_target:
                continue

            # Python AST parsing
            if norm_p.endswith(".py"):
                try:
                    tree = ast.parse(content, filename=norm_p)
                    for node in ast.walk(tree):
                        # Direct imports
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name == target_module_name or alias.name == short_mod_name:
                                    importers.add(norm_p)
                                    impact_items.append(
                                        ImpactItem(
                                            file_path=norm_p,
                                            impact_type="direct_import",
                                            confidence="high",
                                            evidence_snippet=f"import {alias.name}",
                                        )
                                    )
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and (node.module == target_module_name or node.module.endswith("." + short_mod_name) or node.module == short_mod_name):
                                importers.add(norm_p)
                                matched_sym = None
                                if target_symbol:
                                    for alias in node.names:
                                        if alias.name == target_symbol:
                                            matched_sym = target_symbol
                                impact_items.append(
                                    ImpactItem(
                                        file_path=norm_p,
                                        impact_type="direct_import",
                                        symbol_name=matched_sym,
                                        confidence="high",
                                        evidence_snippet=f"from {node.module} import ...",
                                    )
                                )
                except Exception:
                    # Fallback to text check if parse fails
                    if short_mod_name in content:
                        importers.add(norm_p)
                        impact_items.append(
                            ImpactItem(
                                file_path=norm_p,
                                impact_type="direct_import",
                                confidence="low",
                                evidence_snippet=f"Text reference to '{short_mod_name}'",
                            )
                        )
            else:
                # Non-python structural check
                if short_mod_name in content or clean_target in content:
                    importers.add(norm_p)
                    impact_items.append(
                        ImpactItem(
                            file_path=norm_p,
                            impact_type="direct_import",
                            confidence="low",
                            evidence_snippet=f"Text reference to '{clean_target}'",
                        )
                    )

            # Check if this file is a test file exercising target
            if "test" in norm_p.lower():
                if norm_p in importers or short_mod_name in norm_p.lower():
                    tests.add(norm_p)
                    impact_items.append(
                        ImpactItem(
                            file_path=norm_p,
                            impact_type="related_test",
                            confidence="high" if norm_p.endswith(".py") else "medium",
                            evidence_snippet=f"Test file targeting '{short_mod_name}'",
                        )
                    )

        total_affected = len(importers | tests)

        # Build qualitative risk note
        if total_affected == 0:
            risk_note = (
                f"Isolated file '{clean_target}'. No direct external consumers or tests detected "
                "in this snapshot. Minimal blast radius."
            )
        elif total_affected < 4:
            risk_note = (
                f"Moderate blast radius. Changes to '{clean_target}' directly affect {len(importers)} "
                f"module(s) and {len(tests)} test suite(s). Review affected imports carefully."
            )
        else:
            risk_note = (
                f"Broad blast radius. Changes to '{clean_target}' affect {len(importers)} modules "
                f"and {len(tests)} tests. High regression risk across the repository."
            )

        if not is_python:
            risk_note += " (Note: Analysis used structural regex fallback for non-Python assets; relationships may be incomplete)."

        return BlastRadiusReport(
            target_path=clean_target,
            target_symbol=target_symbol,
            affected_files_count=total_affected,
            direct_importers=sorted(list(importers)),
            related_tests=sorted(list(tests)),
            impact_items=impact_items,
            parser_tier=parser_tier,
            qualitative_risk_note=risk_note,
        )
