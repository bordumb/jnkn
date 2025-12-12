"""
Diff Command - Semantic Impact Analysis for PRs.

Analyzes what changed between two git refs and calculates risk.
"""

import json
import logging
import sys
import time
from pathlib import Path

import click
from rich.console import Console

from ...analysis.diff_analyzer import DiffAnalyzer
from ...analysis.reviewers import ReviewerSuggester
from ...analysis.risk import RiskAnalyzer, RiskLevel
from ...cli.formatters.diff import DiffFormatter
from ...core.storage.sqlite import SQLiteStorage
from ...git.diff_engine import GitDiffEngine, GitError
from ...parsing.engine import ScanConfig, create_default_engine

logger = logging.getLogger(__name__)
console = Console()


@click.command()
@click.argument("base_ref", default="origin/main")
@click.argument("head_ref", default="HEAD")
@click.option("--repo", "-r", default=".", help="Path to git repository")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), help="Write output to file")
@click.option(
    "--fail-on-risk",
    type=click.Choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
    help="Exit 1 if risk level meets or exceeds threshold",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON (shortcut for --format json)")
def diff(
    base_ref: str,
    head_ref: str,
    repo: str,
    output_format: str,
    output: str | None,
    fail_on_risk: str | None,
    as_json: bool,
):
    """
    Analyze semantic impact of changes between git refs.

    Generates a risk assessment showing what changed and its downstream impact.
    Perfect for PR reviews and CI gates.

    \b
    Examples:
        # Compare current changes against main
        jnkn diff origin/main HEAD

        # Generate PR comment markdown
        jnkn diff origin/main HEAD --format markdown

        # CI gate: fail if risk is HIGH or above
        jnkn diff origin/main HEAD --fail-on-risk HIGH

        # Output to file
        jnkn diff origin/main HEAD --format markdown -o pr_comment.md
    """
    if as_json:
        output_format = "json"

    repo_path = Path(repo).absolute()
    start_time = time.time()

    try:
        # 1. Initialize Git Engine
        git_engine = GitDiffEngine(repo_path)

        # 2. Get changed files from git
        with console.status("[bold]Fetching changed files...[/bold]"):
            changed_files = git_engine.get_changed_files(base_ref, head_ref)

        if not changed_files:
            console.print("[green]✓[/green] No files changed between refs.")
            sys.exit(0)

        console.print(f"[dim]Found {len(changed_files)} changed file(s)[/dim]")

        # 3. Build/Load dependency graph for HEAD
        with console.status("[bold]Scanning dependencies...[/bold]"):
            db_path = repo_path / ".jnkn" / "jnkn.db"

            if db_path.exists():
                # Use existing graph
                storage = SQLiteStorage(db_path)
                graph = storage.load_graph()
            else:
                # Build graph on the fly
                storage = SQLiteStorage(repo_path / ".jnkn" / "diff_temp.db")
                storage.clear()
                engine = create_default_engine()
                result = engine.scan_and_store(
                    storage, ScanConfig(root_dir=repo_path, incremental=False)
                )
                graph = storage.load_graph()

        # 4. Analyze diff
        with console.status("[bold]Analyzing impact...[/bold]"):
            diff_analyzer = DiffAnalyzer(graph)
            diff_report = diff_analyzer.analyze_from_changed_files(
                graph=graph,
                changed_files=changed_files,
                base_ref=base_ref,
                head_ref=head_ref,
            )
            diff_report.scan_duration_ms = (time.time() - start_time) * 1000

        # 5. Calculate risk
        risk_analyzer = RiskAnalyzer()
        risk_assessment = risk_analyzer.analyze(diff_report)

        # 6. Suggest reviewers
        suggester = ReviewerSuggester(repo_path)
        affected_paths = list(diff_report.get_affected_paths())
        reviewers = suggester.suggest(affected_paths)

        # 7. Format output
        formatter = DiffFormatter(console)

        if output_format == "json":
            result = {
                "meta": {
                    "base_ref": base_ref,
                    "head_ref": head_ref,
                    "duration_ms": diff_report.scan_duration_ms,
                },
                "risk": risk_assessment.to_dict(),
                "changes": diff_report.to_dict(),
                "reviewers": [r.to_dict() for r in reviewers],
            }
            output_content = json.dumps(result, indent=2)

            if output:
                Path(output).write_text(output_content)
                console.print(f"[green]✓[/green] Written to {output}")
            else:
                print(output_content)

        elif output_format == "markdown":
            output_content = formatter.generate_markdown(diff_report, risk_assessment, reviewers)

            if output:
                Path(output).write_text(output_content)
                console.print(f"[green]✓[/green] Written to {output}")
            else:
                print(output_content)

        else:  # text
            formatter.print_summary(diff_report, risk_assessment, reviewers)

            if output:
                # For text output to file, generate markdown
                output_content = formatter.generate_markdown(
                    diff_report, risk_assessment, reviewers
                )
                Path(output).write_text(output_content)
                console.print(f"[green]✓[/green] Written to {output}")

        # 8. CI Gate
        if fail_on_risk:
            threshold = RiskLevel(fail_on_risk)
            levels_ordered = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

            current_idx = levels_ordered.index(risk_assessment.level)
            threshold_idx = levels_ordered.index(threshold)

            if current_idx >= threshold_idx:
                console.print(
                    f"\n[red]✗[/red] Risk level {risk_assessment.level.value} "
                    f"meets or exceeds threshold {fail_on_risk}"
                )
                sys.exit(1)

        sys.exit(0)

    except GitError as e:
        console.print(f"[red]Git error:[/red] {e.message}")
        if e.stderr:
            console.print(f"[dim]{e.stderr}[/dim]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Diff command failed")
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
