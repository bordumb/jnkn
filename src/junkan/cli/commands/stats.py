"""
Stats and Clear Commands - Graph statistics and cleanup.
"""

import click
import json
from pathlib import Path

from ..utils import echo_success, echo_error, load_graph


@click.command()
@click.option("-g", "--graph", "graph_file", default=".",
              help="Path to graph JSON file")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def stats(graph_file: str, as_json: bool):
    """
    Show graph statistics.
    
    Displays node counts, edge counts, and breakdowns by type.
    
    \b
    Examples:
        junkan stats
        junkan stats --json
    """
    graph_path = Path(graph_file)
    
    if not graph_path.exists():
        echo_error(f"Graph not found: {graph_file}")
        click.echo("Run 'junkan scan' first to create the graph.")
        return
    
    graph = load_graph(graph_file)
    if graph is None:
        return
    
    s = graph.stats()
    
    if as_json:
        click.echo(json.dumps(s, indent=2))
        return
    
    click.echo()
    click.echo(f"📊 {click.style('Graph Statistics', bold=True)}")
    click.echo("═" * 40)
    click.echo()
    click.echo(f"Source: {graph_file}")
    click.echo(f"Size: {graph_path.stat().st_size / 1024:.1f} KB")
    click.echo()
    click.echo(f"Nodes: {s['total_nodes']}")
    click.echo(f"Edges: {s['total_edges']}")
    
    if s.get("nodes_by_type"):
        click.echo()
        click.echo("Nodes by type:")
        for node_type, count in s["nodes_by_type"].items():
            click.echo(f"  {node_type}: {count}")
    
    if s.get("edges_by_type"):
        click.echo()
        click.echo("Edges by type:")
        for edge_type, count in s["edges_by_type"].items():
            click.echo(f"  {edge_type}: {count}")
    
    if "orphans" in s:
        click.echo()
        click.echo(f"Orphans: {s['orphans']}")
    
    click.echo()


@click.command()
@click.option("-g", "--graph", "graph_file", default=".",
              help="Path to graph JSON file")
@click.option("--all", "clear_all", is_flag=True,
              help="Clear all .junkan data")
@click.confirmation_option(prompt="Are you sure you want to clear the data?")
def clear(graph_file: str, clear_all: bool):
    """
    Clear graph data.
    
    \b
    Examples:
        junkan clear
        junkan clear --all
    """
    cleared = []
    
    if clear_all:
        junkan_dir = Path(".junkan")
        if junkan_dir.exists():
            import shutil
            shutil.rmtree(junkan_dir)
            cleared.append(".junkan/")
    else:
        graph_path = Path(graph_file)
        if graph_path.exists():
            graph_path.unlink()
            cleared.append(graph_file)
    
    if cleared:
        echo_success(f"Cleared: {', '.join(cleared)}")
    else:
        click.echo("Nothing to clear.")