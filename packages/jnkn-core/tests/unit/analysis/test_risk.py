"""
Unit tests for the Risk Analysis Engine.
"""

import pytest
from unittest.mock import MagicMock

from jnkn.analysis.risk import RiskAnalyzer, RiskLevel, RiskAssessment
from jnkn.analysis.diff_analyzer import DiffReport, NodeChange, ChangeType
from jnkn.core.types import Node, NodeType


@pytest.fixture
def analyzer():
    return RiskAnalyzer()


@pytest.fixture
def mock_node():
    """Helper to create a dummy node."""
    def _create(node_type=NodeType.CODE_FILE, name="test"):
        return Node(id=f"{node_type}:{name}", name=name, type=node_type)
    return _create


class TestRiskAnalyzer:
    """Tests for RiskAnalyzer scoring logic."""

    def test_empty_diff_is_perfect_score(self, analyzer):
        """An empty diff should have a score of 100."""
        report = DiffReport(base_ref="main", head_ref="feat")
        assessment = analyzer.analyze(report)
        
        assert assessment.score == 100
        assert assessment.level == RiskLevel.LOW
        assert not assessment.factors

    def test_infra_removal_penalty(self, analyzer, mock_node):
        """Removing infrastructure should incur a high penalty."""
        node = mock_node(NodeType.INFRA_RESOURCE, "db_instance")
        change = NodeChange(
            node=node,
            change_type=ChangeType.REMOVED,
            blast_radius=5
        )
        report = DiffReport(base_ref="main", head_ref="feat", removed_nodes=[change])
        
        assessment = analyzer.analyze(report)
        
        # Calculation:
        # 1. Base penalty for INFRA_RESOURCE REMOVED is 40
        # 2. Blast radius 5 multiplier is 1.2 -> Penalty = 48
        # 3. Breaking Change Penalty (because removal of infra is breaking):
        #    1 breaking change * 5 points = 5
        
        # Total Penalty = 48 + 5 = 53
        # Score = 100 - 53 = 47
        
        assert assessment.score == 47
        assert assessment.level == RiskLevel.HIGH
        
        # Should have 2 factors: removal penalty + breaking change penalty
        assert len(assessment.factors) == 2
        
        # Verify individual factors
        removal_factor = next(f for f in assessment.factors if "removed" in f.name or "REMOVED" in f.name)
        assert removal_factor.score_impact == 48
        
        breaking_factor = next(f for f in assessment.factors if f.name == "breaking_changes")
        assert breaking_factor.score_impact == 5

    def test_high_blast_radius_multiplier(self, analyzer, mock_node):
        """High blast radius should multiply the risk penalty."""
        node = mock_node(NodeType.ENV_VAR, "API_KEY")
        
        # Modified env var (Base penalty 15) with 55 consumers (>50 -> 2.0x)
        change = NodeChange(
            node=node,
            change_type=ChangeType.MODIFIED,
            blast_radius=55
        )
        report = DiffReport(base_ref="main", head_ref="feat", modified_nodes=[change])
        
        assessment = analyzer.analyze(report)
        
        # Penalty = 15 * 2.0 = 30
        assert assessment.score == 70
        assert assessment.level == RiskLevel.MEDIUM
        assert assessment.factors[0].severity == RiskLevel.CRITICAL  # Factor severity

    def test_breaking_changes_bonus_penalty(self, analyzer, mock_node):
        """Presence of breaking changes adds an extra penalty."""
        # Removing an env var is breaking
        node = mock_node(NodeType.ENV_VAR, "OLD_VAR")
        change = NodeChange(
            node=node,
            change_type=ChangeType.REMOVED,
            blast_radius=1  # Has consumers, so it's breaking
        )
        
        # Ensure is_breaking logic works (mocked implicitly via NodeChange logic in real class)
        # But here we construct a real NodeChange which uses the real property logic
        assert change.is_breaking
        
        report = DiffReport(base_ref="main", head_ref="feat", removed_nodes=[change])
        
        assessment = analyzer.analyze(report)
        
        # Base Penalty: ENV_VAR REMOVED (30) * Multiplier (1.0 for blast 1) = 30
        # Breaking Bonus: 1 breaking change * 5 = 5
        # Total Penalty = 35
        # Score = 65
        
        assert assessment.score == 65
        
        # Should have 2 factors: one for the change, one for "breaking_changes"
        assert len(assessment.factors) == 2
        factor_names = [f.name for f in assessment.factors]
        assert "breaking_changes" in factor_names

    def test_score_normalization(self, analyzer, mock_node):
        """Score should never go below 0."""
        # Create enough changes to exceed 100 penalty
        changes = []
        for i in range(5):
            node = mock_node(NodeType.INFRA_RESOURCE, f"res_{i}")
            changes.append(NodeChange(
                node=node,
                change_type=ChangeType.REMOVED,
                blast_radius=0
            ))
            
        report = DiffReport(base_ref="main", head_ref="feat", removed_nodes=changes)
        assessment = analyzer.analyze(report)
        
        # 5 * 40 = 200 penalty
        assert assessment.score == 0
        assert assessment.level == RiskLevel.CRITICAL

    def test_generate_summary_low_risk(self, analyzer):
        """Summary for perfect score."""
        report = DiffReport(base_ref="a", head_ref="b")
        assessment = analyzer.analyze(report)
        assert "Low risk" in assessment.summary

    def test_generate_summary_high_risk(self, analyzer, mock_node):
        """Summary should highlight infrastructure and breaking changes."""
        node = mock_node(NodeType.INFRA_RESOURCE, "db")
        change = NodeChange(
            node=node,
            change_type=ChangeType.MODIFIED,
            blast_radius=10
        )
        report = DiffReport(base_ref="a", head_ref="b", modified_nodes=[change])
        
        assessment = analyzer.analyze(report)
        
        assert "infrastructure modifications" in assessment.summary
        assert "significant blast radius" in assessment.summary