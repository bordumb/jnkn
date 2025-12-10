"""Unit tests for CLI utilities."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jnkn.cli.utils import load_graph, echo_low_node_warning


class TestUtils:
    """Tests for shared CLI utility functions."""

    def test_load_graph_from_json(self, tmp_path):
        """Test loading a legacy JSON graph file."""
        f = tmp_path / "graph.json"
        f.write_text(json.dumps({"nodes": [], "edges": []}))
        
        with patch("jnkn.cli.utils.LineageGraph") as mock_cls:
            mock_instance = mock_cls.return_value
            graph = load_graph(str(f))
            assert graph is not None
            mock_instance.load_from_dict.assert_called_once()

    def test_load_graph_from_db(self, tmp_path):
        """Test loading a SQLite DB graph file."""
        f = tmp_path / "graph.db"
        f.touch()

        with patch("jnkn.cli.utils.SQLiteStorage") as mock_storage_cls:
            mock_storage = mock_storage_cls.return_value
            mock_graph = MagicMock()
            mock_storage.load_graph.return_value = mock_graph

            graph = load_graph(str(f))

            assert graph == mock_graph
            mock_storage_cls.assert_called_with(f)

    def test_load_graph_missing_file(self, tmp_path, capsys):
        """Test behavior when the specified file does not exist."""
        missing = tmp_path / "missing.json"
        graph = load_graph(str(missing))
        assert graph is None
        captured = capsys.readouterr()
        assert f"File not found: {missing}" in captured.err

    def test_echo_low_node_warning(self, capsys):
        """Test the low node count warning output."""
        echo_low_node_warning(3)
        captured = capsys.readouterr()
        
        assert "Low node count detected!" in captured.out
        assert "(3 nodes found)" in captured.out