# FILE: tests/unit/graph/test_visualize.py
"""
Unit tests for the visualization module (Smoke Tests).
"""

from unittest.mock import MagicMock
import pytest
import json
from jnkn.graph.visualize import generate_html
from jnkn.core.types import Node, Edge, NodeType, RelationshipType

class TestVisualize:
    @pytest.fixture
    def mock_graph(self):
        """Create a mock IGraph with diverse node and edge types."""
        graph = MagicMock()
        
        # Mock iter_nodes
        nodes = [
            Node(id="env:DB_HOST", name="DB_HOST", type=NodeType.ENV_VAR),
            Node(id="infra:aws_db_instance.main", name="main", type=NodeType.INFRA_RESOURCE),
            Node(id="file://app.py", name="app.py", type=NodeType.CODE_FILE)
        ]
        graph.iter_nodes.return_value = nodes
        
        # Mock iter_edges
        edges = [
            Edge(source_id="infra:aws_db_instance.main", target_id="env:DB_HOST", type=RelationshipType.PROVIDES),
            Edge(source_id="file://app.py", target_id="env:DB_HOST", type=RelationshipType.READS)
        ]
        graph.iter_edges.return_value = edges
        
        # Mock to_dict (used by the new implementation)
        graph.to_dict.return_value = {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges]
        }
        
        return graph

    def test_generate_html_integrity(self, mock_graph):
        """
        Smoke Test: Ensure HTML is generated and data is injected correctly.
        """
        html = generate_html(mock_graph)
        
        # 1. Structure Check
        assert "<!DOCTYPE html>" in html
        assert "<title>Jnkn Impact Browser</title>" in html
        
        # 2. Data Injection Check
        # The placeholder should be GONE
        assert "__GRAPH_DATA__" not in html
        
        # The actual data should be PRESENT
        assert 'id": "env:DB_HOST"' in html
        assert 'source_id": "infra:aws_db_instance.main"' in html
        
        # 3. New UI Component Check
        # Verify v3.1 Miller Columns CSS/JS exists
        assert "columns-wrapper" in html
        assert "renderRootColumn()" in html
        assert "inspector" in html

    def test_serialization_safety(self, mock_graph):
        """
        Ensure complex types (Enums, Datetimes) don't crash the JSON serializer.
        """
        # This implicitly tests the _json_default helper in visualize.py
        html = generate_html(mock_graph)
        
        # Check if Enum values were serialized as strings
        assert '"type": "env_var"' in html or '"type": "ENV_VAR"' in html
        assert '"type": "provides"' in html or '"type": "PROVIDES"' in html