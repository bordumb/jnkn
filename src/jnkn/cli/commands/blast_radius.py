"""
Blast Radius Command - Calculate downstream impact.
"""

import json
from pathlib import Path

import click

from ..utils import echo_error, load_graph


@click.command("blast-radius")
@click.argument("artifacts", nargs=-1)
@click.option("-d", "--db", "db_path", default=".jnkn/jnkn.db",
              help="Path to Junkan database or graph.json")
@click.option("--max-depth", default=-1, type=int,
              help="Maximum traversal depth (-1 for unlimited)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def blast_radius(artifacts: tuple, db_path: str, max_depth: int, as_json: bool):
    """
    Calculate downstream impact for changed artifacts.
    
    \b
    Examples:
        jnkn blast-radius env:DB_HOST
        jnkn blast-radius warehouse.dim_users
        jnkn blast-radius src/models.py infra:payment_db
    """
    if not artifacts:
        echo_error("Provide at least one artifact to analyze")
        click.echo("Examples:")
        click.echo("  jnkn blast-radius env:DB_HOST")
        click.echo("  jnkn blast-radius warehouse.dim_users")
        return

    db_file = Path(db_path)
    
    # Handle directory input - look for known files
    if db_file.is_dir():
        if (db_file / "jnkn.db").exists():
            db_file = db_file / "jnkn.db"
        elif (db_file / "graph.json").exists():
            db_file = db_file / "graph.json"
        else:
            db_file = db_file / "jnkn.db"  # Default

    if not db_file.exists():
        echo_error(f"Database not found: {db_file}")
        click.echo("Run 'jnkn scan' first to build the dependency graph.")
        return

    # Use SQLite storage for .db files, fallback to JSON for development
    if db_file.suffix == ".db":
        _run_with_sqlite(db_file, artifacts, max_depth, as_json)
    else:
        _run_with_json(db_file, artifacts, max_depth, as_json)


def _run_with_sqlite(db_file: Path, artifacts: tuple, max_depth: int, as_json: bool):
    """Run blast radius using SQLite storage."""
    from ...core.storage.sqlite import SQLiteStorage
    
    storage = SQLiteStorage(db_file)
    
    try:
        all_downstream = set()
        resolved_artifacts = []

        for artifact in artifacts:
            resolved_artifacts.append(artifact)
            downstream = storage.query_descendants(artifact, max_depth)
            all_downstream.update(downstream)

        result = {
            "source_artifacts": resolved_artifacts,
            "total_impacted_count": len(all_downstream),
            "impacted_artifacts": sorted(all_downstream),
            "breakdown": _categorize(all_downstream),
        }

        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            _print_result(result)
    finally:
        storage.close()


def _run_with_json(graph_path: Path, artifacts: tuple, max_depth: int, as_json: bool):
    """Run blast radius using JSON graph file (development fallback)."""
    graph = load_graph(str(graph_path))
    if graph is None:
        return

    all_downstream = set()
    resolved_artifacts = []

    for artifact in artifacts:
        # Resolve partial names
        if not artifact.startswith(("data:", "file:", "job:", "env:", "infra:")):
            matches = graph.find_nodes(artifact)
            if matches:
                artifact = matches[0]
            else:
                echo_error(f"No match found for: {artifact}")
                continue

        resolved_artifacts.append(artifact)
        downstream = graph.downstream(artifact, max_depth)
        all_downstream.update(downstream)

    result = {
        "source_artifacts": resolved_artifacts,
        "total_impacted_count": len(all_downstream),
        "impacted_artifacts": sorted(all_downstream),
        "breakdown": _categorize(all_downstream),
    }

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        _print_result(result)


def _categorize(artifacts: set) -> dict:
    """Categorize artifacts by type."""
    breakdown = {
        "data": [],
        "code": [],
        "config": [],
        "infra": [],
        "other": [],
    }

    for art in artifacts:
        if art.startswith("data:"):
            breakdown["data"].append(art)
        elif art.startswith(("file:", "job:")):
            breakdown["code"].append(art)
        elif art.startswith("env:"):
            breakdown["config"].append(art)
        elif art.startswith("infra:"):
            breakdown["infra"].append(art)
        else:
            breakdown["other"].append(art)

    return breakdown


def _print_result(result: dict):
    """Pretty print blast radius result."""
    click.echo()
    click.echo(click.style("Blast Radius Analysis", bold=True))
    click.echo("=" * 60)

    click.echo()
    click.echo(click.style("Source artifacts:", bold=True))
    for art in result.get("source_artifacts", []):
        click.echo(f"  - {art}")

    click.echo()
    total = result.get("total_impacted_count", 0)
    click.echo(f"{click.style('Total impacted:', bold=True)} {total} artifacts")

    breakdown = result.get("breakdown", {})
    if breakdown:
        click.echo()
        click.echo(click.style("By category:", bold=True))
        for category, items in breakdown.items():
            if items:
                click.echo(f"  {category}: {len(items)}")

    click.echo()
    click.echo(click.style("Impacted artifacts:", bold=True))
    for art in result.get("impacted_artifacts", [])[:20]:
        click.echo(f"  - {art}")

    if total > 20:
        click.echo(f"  ... and {total - 20} more")

    click.echo()
