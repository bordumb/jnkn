"""
Diff Command - Semantic Impact Analysis for PRs.

Analyzes what changed between two git refs and calculates risk.
Now implements "Time Travel" parsing to reconstruct the base state.
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
from ...core.graph import DependencyGraph
from ...core.storage.sqlite import SQLiteStorage
from ...core.types import Edge, Node
from ...git.diff_engine import FileStatus, GitDiffEngine, GitError
from ...parsing.engine import ScanConfig, create_default_engine

logger = logging.getLogger(__name__)
console = Console()


def _build_virtual_base_graph(
    repo_path: Path,
    head_graph: DependencyGraph,
    git_engine: GitDiffEngine,
    base_ref: str,
    head_ref: str,
) -> DependencyGraph:
    """
    Constructs the dependency graph for the Base Ref.

    Optimization Strategy:
    1. For files that HAVEN'T changed, reuse nodes/edges from Head Graph.
    2. For files that HAVE changed (Modified/Deleted), fetch content from git
       at base_ref, parse it, and add those nodes/edges.
    """
    base_graph = DependencyGraph()
    parser_engine = create_default_engine()

    # 1. Get list of changed files
    changed_files = git_engine.get_changed_files(base_ref, head_ref)
    changed_paths = {str(f.path).lstrip("./") for f in changed_files}

    # 2. Re-use Unchanged Nodes (Optimization)
    # We iterate head graph. If a node belongs to a file that wasn't changed,
    # it must be the same in Base.
    for node in head_graph.iter_nodes():
        if not node.path:
            continue

        node_path = str(node.path).lstrip("./")
        if node_path not in changed_paths:
            base_graph.add_node(node)

    # Re-use edges where both source/target are unchanged
    for edge in head_graph.iter_edges():
        src = head_graph.get_node(edge.source_id)
        tgt = head_graph.get_node(edge.target_id)

        if src and tgt and src.path and tgt.path:
            src_path = str(src.path).lstrip("./")
            tgt_path = str(tgt.path).lstrip("./")

            if src_path not in changed_paths and tgt_path not in changed_paths:
                base_graph.add_edge(edge)

    # 3. Parse Changed Files at Base Revision
    # This finds nodes that were Modified or Deleted
    with console.status(f"[bold]Reconstructing {base_ref} state...[/bold]"):
        for cf in changed_files:
            if cf.status == FileStatus.ADDED:
                continue  # Didn't exist in base

            # Use old_path for renames, otherwise path
            path_to_fetch = cf.old_path if cf.old_path else cf.path

            content = git_engine.get_file_content_at_ref(base_ref, str(path_to_fetch))
            if not content:
                continue

            # Parse virtual content
            # We use the parse_file method but pass the content explicitly
            # The parser will return Nodes/Edges. We filter for this file.

            # Note: We need a temporary file path object for the parser routing logic
            # but we pass the raw bytes from git.
            virtual_path = repo_path / path_to_fetch

            # Since parser engine usually expects to read from disk or uses the path extension
            # to pick the parser, passing the path is fine even if file doesn't match content on disk.
            # We use _parse_file_full's internal logic which we can access via parse_file generator.

            # We have to bypass the engine's file reading and go straight to parsers
            # because engine.scan_and_store is disk-bound.

            parsers = parser_engine.registry.get_parsers_for_file(virtual_path)
            for parser in parsers:
                if parser.can_parse(virtual_path, content.encode("utf-8")):
                    try:
                        for item in parser.parse(virtual_path, content.encode("utf-8")):
                            if isinstance(item, Node):
                                base_graph.add_node(item)
                            elif isinstance(item, Edge):
                                base_graph.add_edge(item)
                    except Exception as e:
                        logger.warning(f"Failed to parse base version of {path_to_fetch}: {e}")

    return base_graph


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
    """
    if as_json:
        output_format = "json"

    repo_path = Path(repo).absolute()
    start_time = time.time()

    try:
        # 1. Initialize Git Engine
        git_engine = GitDiffEngine(repo_path)

        # 2. Get changed files
        with console.status("[bold]Fetching changed files...[/bold]"):
            changed_files = git_engine.get_changed_files(base_ref, head_ref)

        if not changed_files:
            console.print("[green]✓[/green] No files changed between refs.")
            sys.exit(0)

        console.print(f"[dim]Found {len(changed_files)} changed file(s)[/dim]")

        # 3. Build HEAD Graph (Current State)
        with console.status("[bold]Scanning HEAD state...[/bold]"):
            db_path = repo_path / ".jnkn" / "jnkn.db"

            if db_path.exists():
                # Use cached graph if available
                storage = SQLiteStorage(db_path)
                head_graph = storage.load_graph()
            else:
                # Build fresh
                storage = SQLiteStorage(repo_path / ".jnkn" / "diff_temp.db")
                storage.clear()
                engine = create_default_engine()
                result = engine.scan_and_store(
                    storage, ScanConfig(root_dir=repo_path, incremental=False)
                )
                head_graph = storage.load_graph()

        # 4. Build BASE Graph (Time Travel)
        # This allows us to see what was REMOVED
        base_graph = _build_virtual_base_graph(
            repo_path, head_graph, git_engine, base_ref, head_ref
        )

        # 5. Analyze Diff
        with console.status("[bold]Comparing graphs...[/bold]"):
            diff_analyzer = DiffAnalyzer()
            # Now we can use the robust compare() method
            diff_report = diff_analyzer.compare(
                base_graph=base_graph,
                head_graph=head_graph,
                base_ref=base_ref,
                head_ref=head_ref,
            )
            diff_report.scan_duration_ms = (time.time() - start_time) * 1000
            # Inject files changed count from git for accuracy
            diff_report.files_changed = len(changed_files)

        # 6. Calculate Risk
        risk_analyzer = RiskAnalyzer()
        risk_assessment = risk_analyzer.analyze(diff_report)

        # 7. Suggest Reviewers
        suggester = ReviewerSuggester(repo_path)
        affected_paths = list(diff_report.get_affected_paths())
        reviewers = suggester.suggest(affected_paths)

        # 8. Format Output
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
                output_content = formatter.generate_markdown(
                    diff_report, risk_assessment, reviewers
                )
                Path(output).write_text(output_content)
                console.print(f"[green]✓[/green] Written to {output}")

        # 9. CI Gate
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
