"""
Regression tests for Confidence Scoring heuristics.

Verifies that specific "bad patterns" (like 'id' matching 'id') are suppressed
while valid patterns are preserved.
"""

import pytest
from jnkn.core.confidence import (
    ConfidenceCalculator, 
    ConfidenceConfig, 
    PenaltyType
)
from jnkn.core.types import NodeType

@pytest.fixture
def calculator():
    return ConfidenceCalculator(ConfidenceConfig())

class TestBadMatchSuppression:
    
    def test_generic_id_match_is_crushed(self, calculator):
        """
        Verify that 'id' matching 'id' receives a Generic Match penalty
        and results in a very low score.
        """
        result = calculator.calculate(
            source_name="id",
            target_name="id",
            source_tokens=["id"],
            target_tokens=["id"],
            source_type=NodeType.INFRA_RESOURCE,
            target_type=NodeType.ENV_VAR
        )
        
        # Expectation: Score should be decimated (< 0.2)
        assert result.score < 0.2
        
        # Verify specific penalty applied
        penalties = [p['penalty_type'] for p in result.penalties]
        assert PenaltyType.GENERIC_MATCH in penalties
        assert PenaltyType.COMMON_TOKEN in penalties

    def test_generic_name_match_is_crushed(self, calculator):
        """Verify 'name' matching 'name' is suppressed."""
        result = calculator.calculate(
            source_name="name",
            target_name="name",
            source_tokens=["name"],
            target_tokens=["name"],
            source_type=NodeType.INFRA_RESOURCE,
            target_type=NodeType.ENV_VAR
        )
        assert result.score < 0.2
        assert PenaltyType.GENERIC_MATCH in [p['penalty_type'] for p in result.penalties]

    def test_invalid_direction_penalty(self, calculator):
        """
        Verify that EnvVar -> Infra flow (reverse of normal) is penalized.
        """
        result = calculator.calculate(
            source_name="DB_HOST",
            target_name="db_host",
            source_tokens=["db", "host"],
            target_tokens=["db", "host"],
            source_type=NodeType.ENV_VAR,        # Source is EnvVar
            target_type=NodeType.INFRA_RESOURCE  # Target is Infra
        )
        
        # This implies EnvVar PROVIDES for Infra, which is usually wrong.
        assert result.score < 0.5
        assert PenaltyType.INVALID_DIRECTION in [p['penalty_type'] for p in result.penalties]

class TestGoodMatchPreservation:
    
    def test_valid_db_host_match(self, calculator):
        """Verify that a legitimate DB host match remains high confidence."""
        result = calculator.calculate(
            source_name="payment_db_host",
            target_name="PAYMENT_DB_HOST",
            source_tokens=["payment", "db", "host"],
            target_tokens=["payment", "db", "host"],
            source_type=NodeType.INFRA_RESOURCE,
            target_type=NodeType.ENV_VAR
        )
        
        # Should be high confidence (> 0.8)
        assert result.score > 0.8
        # Should NOT have generic penalties
        penalties = [p['penalty_type'] for p in result.penalties]
        assert PenaltyType.GENERIC_MATCH not in penalties
        assert PenaltyType.INVALID_DIRECTION not in penalties

    def test_partial_generic_is_ok(self, calculator):
        """
        Verify that containing a generic term (like 'id') doesn't kill the match
        if there are other specific tokens (like 'payment').
        """
        result = calculator.calculate(
            source_name="payment_account_id",
            target_name="PAYMENT_ACCOUNT_ID",
            source_tokens=["payment", "account", "id"],
            target_tokens=["payment", "account", "id"],
            source_type=NodeType.INFRA_RESOURCE,
            target_type=NodeType.ENV_VAR
        )
        
        # Should still match well because "payment" is specific
        assert result.score > 0.7