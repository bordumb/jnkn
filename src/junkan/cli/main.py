"""
Junkan CLI.

Provides command-line interface for:
- scan: Parse codebase and build dependency graph
- blast-radius: Calculate impact of changes
- stats: Show graph statistics
"""

import click
import json
from pathlib import Path
from datetime import datetime
from typing import List, Set

from ..core.graph import DependencyGraph
from ..core.stitching import Stitcher, MatchConfig
from ..core.storage.sqlite import SQLiteStorage
from ..core.types import Node, Edge, ScanMetadata
from ..languages.parser import TreeSitterEngine, LanguageConfig
from ..analysis.blast_radius import BlastRadiusAnalyzer


def create_engine() -> TreeSitterEngine:
    """Create and configure the parsing engine."""
    engine = TreeSitterEngine()
    base_dir = Path(__file__).resolve().parent.parent / "languages"
    
    engine.register_language(LanguageConfig(
        name="python",
        extensions=[".py"],
        query_paths=[
            base_dir / "python/imports.scm",
            base_dir / "python/definitions.scm",
        ]
    ))
    
    engine.register_language(LanguageConfig(
        name="hcl",
        tree_sitter_name="hcl",
        extensions=[".tf"],
        query_paths=[
            base_dir / "terraform/resources.scm",
        ]
    ))
    
    return engine


# Skip these directories during scanning
SKIP_DIRS: Set[str] = {
    ".git", ".junkan", "__pycache__", "node_modules",
    ".venv", "venv", "env", ".env", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
}


@click.group()
def main():
    """Junkan: Pre-Flight Impact Analysis Engine."""
    pass


@main.command()
@click.option("--dir", "scan_dir", default=".", help="Codebase root to scan")
@click.option("--db", default=".junkan/junkan.db", help="Path to SQLite DB")
@click.option("--full", is_flag=True, help="Force full rescan (ignore cache)")
@click.option("--min-confidence", default=0.5, help="Minimum stitching confidence")
def scan(scan_dir: str, db: str, full: bool, min_confidence: float):
    """
    Scan codebase and build dependency graph.
    
    Supports incremental scanning - only re-parses changed files.
    """
    graph = DependencyGraph()
    storage = SQLiteStorage(Path(db))
    engine = create_engine()
    
    root = Path(scan_dir)
    click.echo(f"🚀 Scanning {root.absolute()} ...")
    
    # Get existing scan metadata for incremental scanning
    existing_metadata = {
        m.file_path: m for m in storage.get_all_scan_metadata()
    } if not full else {}
    
    # Collect files to scan
    files_to_scan: List[Path] = []
    files_skipped = 0
    files_unchanged = 0
    
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        
        # Skip ignored directories
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        
        # Check if file is supported
        if not engine.supports(path):
            files_skipped += 1
            continue
        
        # Check if file changed (incremental mode)
        str_path = str(path)
        if str_path in existing_metadata and not full:
            current_hash = ScanMetadata.compute_hash(str_path)
            if current_hash == existing_metadata[str_path].file_hash:
                files_unchanged += 1
                continue
            else:
                # File changed - delete old nodes/edges
                storage.delete_nodes_by_file(str_path)
        
        files_to_scan.append(path)
    
    click.echo(f"📁 Found {len(files_to_scan)} files to scan ({files_unchanged} unchanged, {files_skipped} unsupported)")
    
    # Parse files and collect results
    all_nodes: List[Node] = []
    all_edges: List[Edge] = []
    
    for path in files_to_scan:
        for result in engine.parse_file(path):
            if isinstance(result, Node):
                all_nodes.append(result)
                graph.add_node(result)
            else:
                all_edges.append(result)
                graph.add_edge(result)
    
    click.echo(f"✅ Parsed {len(all_nodes)} nodes and {len(all_edges)} edges.")
    
    # Batch save to database
    if all_nodes:
        storage.save_nodes_batch(all_nodes)
    if all_edges:
        storage.save_edges_batch(all_edges)
    
    # Update scan metadata
    file_node_counts: dict = {}
    file_edge_counts: dict = {}
    
    for node in all_nodes:
        if node.path:
            file_node_counts[node.path] = file_node_counts.get(node.path, 0) + 1
    
    for edge in all_edges:
        source_node = graph.get_node(edge.source_id)
        if source_node and source_node.path:
            file_edge_counts[source_node.path] = file_edge_counts.get(source_node.path, 0) + 1
    
    for path in files_to_scan:
        str_path = str(path)
        storage.save_scan_metadata(ScanMetadata(
            file_path=str_path,
            file_hash=ScanMetadata.compute_hash(str_path),
            last_scanned=datetime.utcnow(),
            node_count=file_node_counts.get(str_path, 0),
            edge_count=file_edge_counts.get(str_path, 0),
        ))
    
    # Load full graph for stitching (includes previously scanned files)
    if files_unchanged > 0:
        click.echo("📂 Loading existing graph data...")
        graph = storage.load_graph()
    
    # Stitching phase
    click.echo("🧵 Stitching cross-domain dependencies...")
    config = MatchConfig(min_confidence=min_confidence)
    stitcher = Stitcher(config)
    new_edges = stitcher.stitch(graph)
    
    # Save stitched edges
    if new_edges:
        storage.save_edges_batch(new_edges)
        click.echo(f"✅ Created {len(new_edges)} cross-domain links.")
        
        stats = stitcher.get_stats()
        for rule, count in stats.get("edges_by_rule", {}).items():
            if count > 0:
                click.echo(f"   • {rule}: {count}")
    else:
        click.echo("⚠️  No cross-domain links discovered.")
    
    click.echo("✅ Scan Complete.")


@main.command("blast-radius")
@click.argument("artifacts", nargs=-1)
@click.option("--db", default=".junkan/junkan.db", help="Path to SQLite DB")
@click.option("--max-depth", default=-1, help="Maximum traversal depth")
@click.option("--lazy", is_flag=True, help="Use lazy SQL queries instead of loading graph")
def blast_radius(artifacts, db: str, max_depth: int, lazy: bool):
    """
    Calculate downstream impact for changed artifacts.
    
    Examples:
        junkan blast-radius env:DB_HOST
        junkan blast-radius src/models.py
        junkan blast-radius infra:payment_db
    """
    if not artifacts:
        click.echo("❌ Please provide at least one artifact to analyze.")
        click.echo("Examples:")
        click.echo("  junkan blast-radius env:DB_HOST")
        click.echo("  junkan blast-radius src/models.py")
        return
    
    storage = SQLiteStorage(Path(db))
    
    if lazy:
        analyzer = BlastRadiusAnalyzer(storage=storage)
    else:
        graph = storage.load_graph()
        analyzer = BlastRadiusAnalyzer(graph=graph)
    
    result = analyzer.calculate(list(artifacts), max_depth=max_depth)
    click.echo(json.dumps(result, indent=2, default=str))


@main.command()
@click.option("--db", default=".junkan/junkan.db", help="Path to SQLite DB")
def stats(db: str):
    """Show graph statistics."""
    storage = SQLiteStorage(Path(db))
    stats = storage.get_stats()
    
    click.echo("📊 Graph Statistics")
    click.echo("=" * 40)
    click.echo(f"Schema Version:  {stats['schema_version']}")
    click.echo(f"Total Nodes:     {stats['total_nodes']}")
    click.echo(f"Total Edges:     {stats['total_edges']}")
    click.echo(f"Tracked Files:   {stats['tracked_files']}")
    click.echo(f"DB Size:         {stats['db_size_bytes'] / 1024:.1f} KB")
    
    if stats.get('nodes_by_type'):
        click.echo("\nNodes by Type:")
        for ntype, count in sorted(stats['nodes_by_type'].items()):
            if count > 0:
                click.echo(f"  {ntype}: {count}")
    
    if stats.get('edges_by_type'):
        click.echo("\nEdges by Type:")
        for etype, count in sorted(stats['edges_by_type'].items()):
            if count > 0:
                click.echo(f"  {etype}: {count}")


@main.command()
@click.option("--db", default=".junkan/junkan.db", help="Path to SQLite DB")
@click.confirmation_option(prompt="Are you sure you want to clear all data?")
def clear(db: str):
    """Clear all data from the database."""
    storage = SQLiteStorage(Path(db))
    storage.clear()
    click.echo("✅ Database cleared.")


if __name__ == "__main__":
    main()