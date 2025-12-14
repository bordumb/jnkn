"""
Unit tests for the 'review' interactive command.
"""

from unittest.mock import MagicMock, patch
from click.testing import CliRunner
import pytest

from jnkn.cli.commands.review import review
from jnkn.core.types import Edge, RelationshipType


@pytest.fixture
def mock_graph():
    """Create a mock graph with test edges."""
    graph = MagicMock()
    
    # Create edges with various confidence scores
    edges = [
        Edge(source_id="env:A", target_id="infra:A", type="reads", confidence=0.4),
        Edge(source_id="env:B", target_id="infra:B", type="reads", confidence=0.5),
        Edge(source_id="env:C", target_id="infra:C", type="reads", confidence=0.6),
        Edge(source_id="env:D", target_id="infra:D", type="reads", confidence=0.7),
    ]
    
    graph.iter_edges.return_value = edges
    return graph


@patch("jnkn.cli.commands.review.load_graph")
@patch("jnkn.cli.commands.review.SuppressionStore")
@patch("jnkn.cli.commands.review.Prompt.ask")
@patch("jnkn.cli.commands.review.create_explanation_generator")
def test_review_full_interaction_flow(mock_create_explainer, mock_ask, mock_store_cls, mock_load, mock_graph):
    """
    Test a complete review session with 4 items, exercising all options:
    1. [S] Skip
    2. [E] Explain -> [Y] Confirm
    3. [N] Suppress
    4. [Y] Confirm
    """
    # Setup Graph
    mock_load.return_value = mock_graph
    
    # Setup Explainer Mock
    mock_explainer = mock_create_explainer.return_value
    mock_explainer.explain.return_value = "explanation_obj"
    mock_explainer.format.return_value = "Detailed explanation of why this matched..."

    # Setup Suppression Store
    mock_store = mock_store_cls.return_value
    mock_store.is_suppressed.return_value.suppressed = False

    # Simulate User Inputs for the sequence:
    # Item 1 (env:A): 's' (Skip)
    # Item 2 (env:B): 'e' (Explain) -> Loop repeats item 2 -> 'y' (Confirm)
    # Item 3 (env:C): 'n' (Suppress) -> '1' (Exact pattern) -> 'False positive' (Reason)
    # Item 4 (env:D): 'y' (Confirm)
    mock_ask.side_effect = [
        "s",                # 1. Skip env:A
        "e",                # 2a. Explain env:B
        "y",                # 2b. Confirm env:B
        "n", "1", "Bad match", # 3. Suppress env:C (Action, Pattern, Reason)
        "y"                 # 4. Confirm env:D
    ]

    runner = CliRunner()
    result = runner.invoke(review)

    assert result.exit_code == 0

    # 1. Verify Output Feedback
    # Updated expectation to match "Found 4 potential matches"
    assert "Found 4 potential matches" in result.output
    assert "Skipped." in result.output
    assert "Detailed explanation of why this matched..." in result.output
    # Should see "Match confirmed" twice (Item 2 and Item 4)
    assert result.output.count("Match confirmed.") == 2
    assert "Suppressed pattern" in result.output
    
    # 2. Verify Processing Count
    # Skipped items don't count as "processed". 
    # Processed = Confirmed (2) + Suppressed (1) = 3
    assert "Processed 3 items" in result.output

    # 3. Verify Explainer usage
    # Should be called once for Item 2
    mock_explainer.explain.assert_called_once()
    assert mock_explainer.explain.call_args[0][0] == "env:B"

    # 4. Verify Suppression
    # Should be called once for Item 3
    mock_store.add.assert_called_once()
    args, _ = mock_store.add.call_args
    assert args[0] == "env:C"
    assert args[1] == "infra:C"


@patch("jnkn.cli.commands.review.load_graph")
@patch("jnkn.cli.commands.review.SuppressionStore")
@patch("jnkn.cli.commands.review.Prompt.ask")
def test_review_no_matches_found(mock_ask, mock_store_cls, mock_load, mock_graph):
    """Test behavior when no edges meet criteria."""
    # Setup graph with only high confidence edges (0.9 > default max 0.8)
    edge = Edge(source_id="a", target_id="b", type="reads", confidence=0.9)
    mock_graph.iter_edges.return_value = [edge]
    mock_load.return_value = mock_graph
    
    mock_store = mock_store_cls.return_value
    mock_store.is_suppressed.return_value.suppressed = False

    runner = CliRunner()
    result = runner.invoke(review)

    assert result.exit_code == 0
    assert "No matches found needing review" in result.output


@patch("jnkn.cli.commands.review.load_graph")
@patch("jnkn.cli.commands.review.SuppressionStore")
@patch("jnkn.cli.commands.review.Prompt.ask")
def test_review_quit(mock_ask, mock_store_cls, mock_load, mock_graph):
    """Test quitting the loop early."""
    mock_load.return_value = mock_graph
    mock_store = mock_store_cls.return_value
    mock_store.is_suppressed.return_value.suppressed = False

    # Simulate 'q' input on first item
    mock_ask.return_value = "q"

    runner = CliRunner()
    result = runner.invoke(review)

    assert result.exit_code == 0
    assert "Review complete" in result.output
    assert "Processed 0 items" in result.output