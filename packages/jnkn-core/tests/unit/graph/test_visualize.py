"""
Unit tests for the visualization module (Smoke Tests).
"""

from unittest.mock import MagicMock
import pytest
import json
from jnkn.core.types import Node, Edge, NodeType, RelationshipType
from jnkn.graph.visualizer import generate_html

class TestVisualize:
    @pytest.fixture
    def mock_graph(self):
        """Create a mock IGraph with diverse node and edge types."""
        graph = MagicMock()
        
        # Create concrete objects
        nodes = [
            Node(id="env:DB_HOST", name="DB_HOST", type=NodeType.ENV_VAR),
            Node(id="infra:aws_db_instance.main", name="main", type=NodeType.INFRA_RESOURCE),
            Node(id="file://app.py", name="app.py", type=NodeType.CODE_FILE)
        ]
        
        edges = [
            Edge(source_id="infra:aws_db_instance.main", target_id="env:DB_HOST", type=RelationshipType.PROVIDES),
            Edge(source_id="file://app.py", target_id="env:DB_HOST", type=RelationshipType.READS)
        ]

        # Mock iterators
        graph.iter_nodes.return_value = nodes
        graph.iter_edges.return_value = edges
        
        # Mock to_dict
        graph.to_dict.return_value = {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges]
        }
        
        return graph

    def test_generate_html_integrity(self, mock_graph):
        """
        Smoke Test: Ensure HTML is generated, assets are embedded, and data is injected.
        """
        html = generate_html(mock_graph)
        
        # 1. Structure Check
        assert "<!DOCTYPE html>" in html
        assert "<title>Jnkn Impact Cockpit</title>" in html
        
        # 2. Data Injection Check
        assert "const rawData =" in html
        assert 'id": "env:DB_HOST"' in html
        
        # 3. Design System Check (Mission Control Theme)
        # Verify specific CSS variables from the new theme
        assert "--void:" in html
        assert "--domain-infra:" in html
        assert "--risk-critical:" in html
        
        # 4. JS Application Logic Check
        assert "const AppState =" in html
        assert "const DataProcessor =" in html
        assert "const DOMBuilders =" in html