"""
Jnkn Visualization Engine.

Public API for generating the interactive dependency graph.
"""
import json
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ...core.interfaces import IGraph
from .builder import build_html


def _json_default(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_html(graph: IGraph) -> str:
    """
    Generate the self-contained HTML content for the graph visualization.
    """
    if hasattr(graph, "to_dict"):
        graph_data = graph.to_dict()
    else:
        graph_data = {
            "nodes": [n.model_dump() for n in graph.iter_nodes()],
            "edges": [e.model_dump() for e in graph.iter_edges()],
        }

    # Serialize data once
    json_data = json.dumps(graph_data, default=_json_default)
    return build_html(json_data)


def open_visualization(graph: IGraph, output_path: str = "graph.html") -> str:
    """
    Generate and open the visualization in the browser.
    """
    html_content = generate_html(graph)
    out_file = Path(output_path)
    out_file.write_text(html_content, encoding="utf-8")

    abs_path = out_file.resolve().as_uri()
    webbrowser.open(abs_path)

    return str(out_file)