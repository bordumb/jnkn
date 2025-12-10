"""
Unit tests for the 'scan' command.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Import REAL types to avoid isinstance mocking issues
from jnkn.core.types import Node, Edge, NodeType, RelationshipType

from jnkn.cli.commands.scan import (
    _load_parsers,
    _parse_file,
    _save_output,
    scan,
)


class TestScanCommand:
    """Tests for the main scan command execution."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_graph(self):
        """Mock the DependencyGraph class."""
        with patch("jnkn.cli.commands.scan.DependencyGraph") as mock_cls:
            mock_instance = mock_cls.return_value
            # Default healthy stats
            mock_instance.node_count = 10
            mock_instance.edge_count = 5
            mock_instance.to_dict.return_value = {"nodes": [], "edges": []}
            mock_instance.iter_nodes.return_value = []
            mock_instance.iter_edges.return_value = []
            yield mock_instance

    @pytest.fixture
    def mock_stitcher(self):
        """Mock the Stitcher class."""
        with patch("jnkn.cli.commands.scan.Stitcher") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.stitch.return_value = []  # Return empty list of new edges
            yield mock_instance

    @pytest.fixture
    def mock_load_parsers(self):
        """Mock the parser loader."""
        with patch("jnkn.cli.commands.scan._load_parsers") as mock:
            # Return a dict with a dummy parser
            mock_parser = MagicMock()
            mock_parser.can_parse.return_value = True
            mock_parser.parse.return_value = []
            mock.return_value = {"dummy_parser": mock_parser}
            yield mock

    @pytest.fixture
    def mock_parse_file(self):
        """Mock the file parsing helper."""
        with patch("jnkn.cli.commands.scan._parse_file") as mock:
            mock.return_value = ([], [])  # (nodes, edges)
            yield mock

    @pytest.fixture
    def mock_save_output(self):
        """Mock the output saver."""
        with patch("jnkn.cli.commands.scan._save_output") as mock:
            yield mock

    def test_scan_no_parsers_available(self, runner, mock_load_parsers):
        """Test scanning when no parsers are installed/loaded."""
        mock_load_parsers.return_value = {}  # Empty dict

        with runner.isolated_filesystem():
            result = runner.invoke(scan, ["."])

        assert result.exit_code == 0
        assert "No parsers available" in result.output

    def test_scan_successful_execution(
        self, runner, mock_load_parsers, mock_graph, mock_stitcher, mock_parse_file, mock_save_output
    ):
        """Test a standard successful scan."""
        # Use a real Node object so isinstance checks inside scan.py pass
        real_node = Node(id="test", name="test", type=NodeType.CODE_FILE)
        mock_parse_file.return_value = ([real_node], [])

        with runner.isolated_filesystem():
            # Create a dummy file to find
            Path("test.py").touch()

            result = runner.invoke(scan, ["."])

        assert result.exit_code == 0
        assert "Scanning" in result.output
        assert "Stitching cross-domain dependencies" in result.output
        assert "Scan complete" in result.output
        
        mock_load_parsers.assert_called_once()
        mock_parse_file.assert_called()
        mock_stitcher.stitch.assert_called_once()
        mock_save_output.assert_called_once()

    def test_scan_low_node_count_warning(
        self, runner, mock_load_parsers, mock_graph, mock_parse_file, mock_save_output
    ):
        """Test that finding < 5 nodes triggers the warning."""
        mock_graph.node_count = 3
        
        with runner.isolated_filesystem():
            Path("test.py").touch()
            result = runner.invoke(scan, ["."])

        assert result.exit_code == 0
        assert "Scan complete" not in result.output
        assert "Low node count" in result.output

    def test_scan_file_discovery_recursive(self, runner, mock_load_parsers, mock_parse_file, mock_graph):
        """Test that scan finds files recursively by default."""
        with runner.isolated_filesystem():
            Path("root.py").touch()
            Path("subdir").mkdir()
            Path("subdir/nested.py").touch()

            result = runner.invoke(scan, ["."])

        assert result.exit_code == 0
        assert "Files found: 2" in result.output

    def test_scan_file_discovery_non_recursive(self, runner, mock_load_parsers, mock_parse_file, mock_graph):
        """Test that --no-recursive limits discovery."""
        with runner.isolated_filesystem():
            Path("root.py").touch()
            Path("subdir").mkdir()
            Path("subdir/nested.py").touch()

            result = runner.invoke(scan, [".", "--no-recursive"])

        assert result.exit_code == 0
        assert "Files found: 1" in result.output

    def test_scan_skip_dirs(self, runner, mock_load_parsers, mock_parse_file, mock_graph, mock_save_output):
        """Test that ignored directories are skipped."""
        with runner.isolated_filesystem():
            Path("valid.py").touch()
            
            # Create a skipped directory
            node_modules = Path("node_modules")
            node_modules.mkdir()
            (node_modules / "ignored.js").touch()

            result = runner.invoke(scan, ["."])

        # Should only find valid.py
        assert "Files found: 1" in result.output

    def test_scan_output_file_flag(
        self, runner, mock_load_parsers, mock_graph, mock_parse_file, mock_save_output
    ):
        """Test using the -o flag calls the saver with correct path."""
        with runner.isolated_filesystem():
            Path("test.py").touch()
            result = runner.invoke(scan, [".", "-o", "report.json"])

        assert result.exit_code == 0
        mock_save_output.assert_called_once()
        args = mock_save_output.call_args[0]
        # args: (graph, output_path, verbose)
        assert args[0] == mock_graph 
        assert args[1].name == "report.json"
        assert args[2] is False  # verbose default

    def test_scan_default_output(
        self, runner, mock_load_parsers, mock_graph, mock_parse_file, mock_save_output
    ):
        """Test default output path is now .db."""
        with runner.isolated_filesystem():
            Path("test.py").touch()
            result = runner.invoke(scan, ["."])
            
            mock_save_output.assert_called_once()
            args = mock_save_output.call_args[0]
            expected_path = args[1]
            
            # Verify we default to SQLite DB
            assert expected_path.name == "jnkn.db"
            assert ".jnkn" in str(expected_path)


class TestHelperFunctions:
    """Tests for the internal helper functions in scan.py."""

    def test_load_parsers_success(self):
        """Test loading available parsers."""
        with patch("importlib.import_module") as mock_import:
            # Setup a mock module that has parser classes
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            
            with patch("jnkn.parsing.base.ParserContext"):
                parsers = _load_parsers(Path("."))

        assert isinstance(parsers, dict)

    def test_save_output_json(self, tmp_path):
        """Test saving graph as JSON."""
        mock_graph = MagicMock()
        mock_graph.to_dict.return_value = {"graph": True}
        
        output_file = tmp_path / "graph.json"
        
        _save_output(mock_graph, output_file, verbose=False)
        
        content = output_file.read_text()
        assert '"graph": true' in content

    def test_save_output_db(self, tmp_path):
        """Test saving graph as SQLite DB."""
        mock_graph = MagicMock()
        mock_graph.iter_nodes.return_value = []
        mock_graph.iter_edges.return_value = []
        
        output_file = tmp_path / "graph.db"
        
        with patch("jnkn.cli.commands.scan.SQLiteStorage") as mock_storage_cls:
            mock_storage = mock_storage_cls.return_value
            
            _save_output(mock_graph, output_file, verbose=True)
            
            mock_storage_cls.assert_called_with(output_file)
            mock_storage.save_nodes_batch.assert_called_once()
            mock_storage.close.assert_called_once()

    def test_save_output_unknown(self, capsys, tmp_path):
        """Test saving with unknown extension."""
        mock_graph = MagicMock()
        output_file = tmp_path / "graph.xyz"
        
        _save_output(mock_graph, output_file, verbose=False)
        
        captured = capsys.readouterr()
        assert "Unknown format: .xyz" in captured.err


class TestFileParsingLogic:
    """Tests for the _parse_file helper."""

    def test_parse_file_success(self, tmp_path):
        """Test successful file parsing."""
        f = tmp_path / "test.py"
        f.write_text("content")
        
        mock_parser = MagicMock()
        mock_parser.can_parse.return_value = True
        
        # Use REAL classes to satisfy isinstance checks
        n_inst = Node(id="n1", name="node1", type=NodeType.CODE_FILE)
        e_inst = Edge(source_id="n1", target_id="n2", type=RelationshipType.READS)
        
        mock_parser.parse.return_value = [n_inst, e_inst]
        
        parsers = {"test": mock_parser}
        nodes, edges = _parse_file(f, parsers, verbose=False)

        assert len(nodes) == 1
        assert len(edges) == 1
        assert nodes[0] == n_inst
        assert edges[0] == e_inst

    def test_parse_file_parser_exception(self, tmp_path, capsys):
        """Test handling exception inside a parser."""
        f = tmp_path / "test.py"
        f.write_text("content")
        
        mock_parser = MagicMock()
        mock_parser.can_parse.return_value = True
        mock_parser.parse.side_effect = ValueError("Boom")
        
        parsers = {"test": mock_parser}

        # _parse_file swallows exceptions silently as per implementation
        nodes, edges = _parse_file(f, parsers, verbose=True)
        assert nodes == []