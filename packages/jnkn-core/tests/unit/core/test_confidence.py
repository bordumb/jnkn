"""
Unit tests for the Confidence Calculation Engine.
"""

import pytest
from jnkn.core.confidence import (
    ConfidenceCalculator,
    ConfidenceConfig,
    ConfidenceResult,
    ConfidenceSignal,
    PenaltyType,
    PenaltyResult,
    create_default_calculator,
)
from jnkn.core.types import NodeType

class TestConfidenceCalculator:
    
    @pytest.fixture
    def calculator(self):
        return create_default_calculator()

    def test_initialization(self):
        """Test default initialization and custom config."""
        calc = create_default_calculator()
        assert isinstance(calc.config, ConfidenceConfig)
        
        custom_config = ConfidenceConfig(min_token_overlap_high=5)
        calc_custom = ConfidenceCalculator(config=custom_config)
        assert calc_custom.config.min_token_overlap_high == 5

    def test_normalize(self, calculator):
        """Test name normalization logic."""
        assert calculator._normalize("PAYMENT_DB_HOST") == "paymentdbhost"
        assert calculator._normalize("api.v1-endpoint") == "apiv1endpoint"
        assert calculator._normalize("mixed/SEPARATOR:test") == "mixedseparatortest"

    def test_evaluate_signals_exact_match(self, calculator):
        """Test EXACT_MATCH signal."""
        results = calculator._evaluate_signals(
            "DB_HOST", "DB_HOST", 
            source_tokens=["db", "host"], 
            target_tokens=["db", "host"], 
            matched_tokens=["db", "host"]
        )
        exact = next(r for r in results if r.signal == ConfidenceSignal.EXACT_MATCH)
        assert exact.matched is True
        assert exact.weight == 1.0

    def test_evaluate_signals_normalized_match(self, calculator):
        """Test NORMALIZED_MATCH signal."""
        results = calculator._evaluate_signals(
            "DB_HOST", "db-host", 
            source_tokens=["db", "host"], 
            target_tokens=["db", "host"], 
            matched_tokens=["db", "host"]
        )
        norm = next(r for r in results if r.signal == ConfidenceSignal.NORMALIZED_MATCH)
        assert norm.matched is True
        
        # Ensure exact match is False (don't double count)
        exact = next(r for r in results if r.signal == ConfidenceSignal.EXACT_MATCH)
        assert exact.matched is False

    def test_evaluate_signals_overlap(self, calculator):
        """Test token overlap signals."""
        # High overlap (3 tokens)
        t_list = ["alpha", "beta", "gamma"] 
        results = calculator._evaluate_signals(
            "src", "tgt", t_list, t_list, matched_tokens=t_list
        )
        high = next(r for r in results if r.signal == ConfidenceSignal.TOKEN_OVERLAP_HIGH)
        assert high.matched is True

        # Medium overlap (2 tokens)
        t_med = ["alpha", "beta"]
        results = calculator._evaluate_signals(
            "src", "tgt", t_med, t_med, matched_tokens=t_med
        )
        high = next(r for r in results if r.signal == ConfidenceSignal.TOKEN_OVERLAP_HIGH)
        med = next(r for r in results if r.signal == ConfidenceSignal.TOKEN_OVERLAP_MEDIUM)
        
        assert high.matched is False
        assert med.matched is True

    def test_evaluate_signals_structural(self, calculator):
        """Test Suffix, Prefix, and Contains."""
        # Suffix
        results = calculator._evaluate_signals(
            "host", "db_host", ["host"], ["db", "host"], ["host"]
        )
        suffix = next(r for r in results if r.signal == ConfidenceSignal.SUFFIX_MATCH)
        assert suffix.matched is True

        # Prefix
        results = calculator._evaluate_signals(
            "user", "user_id", ["user"], ["user", "id"], ["user"]
        )
        prefix = next(r for r in results if r.signal == ConfidenceSignal.PREFIX_MATCH)
        assert prefix.matched is True

    def test_evaluate_signals_single_token(self, calculator):
        """Test single token match fallback."""
        # Scenario: "foo" and "bar" don't match structure, but share 1 token "common"
        results = calculator._evaluate_signals(
            "foo", "bar", ["foo", "common"], ["bar", "common"], matched_tokens=["common"]
        )
        single = next(r for r in results if r.signal == ConfidenceSignal.SINGLE_TOKEN)
        assert single.matched is True

    # --- Penalty Tests (Updated API) ---

    def test_evaluate_penalties_short_token(self, calculator):
        """Test SHORT_TOKEN penalty."""
        # "id" is short (< 4 chars) and no long tokens exist
        res = calculator._evaluate_penalties(
            source_name="id", target_name="id",
            matched_tokens=["id"], 
            alternative_match_count=0,
            source_type=None, target_type=None
        )
        short = next(r for r in res if r.penalty_type == PenaltyType.SHORT_TOKEN)
        assert short.multiplier < 1.0

    def test_evaluate_penalties_generic_match(self, calculator):
        """Test GENERIC_MATCH penalty (P0 Fix)."""
        # "id" matching "id" is lexical exact match but semantically weak
        res = calculator._evaluate_penalties(
            source_name="id", target_name="id",
            matched_tokens=["id"],
            alternative_match_count=0,
            source_type=NodeType.INFRA_RESOURCE, target_type=NodeType.ENV_VAR
        )
        
        # Should trigger the GENERIC_MATCH penalty
        generic = next(r for r in res if r.penalty_type == PenaltyType.GENERIC_MATCH)
        assert generic.multiplier == 0.1 # Crushed

    def test_evaluate_penalties_invalid_direction(self, calculator):
        """Test INVALID_DIRECTION penalty."""
        # EnvVar should not "provide" for Infra
        res = calculator._evaluate_penalties(
            source_name="DB_HOST", target_name="db_host",
            matched_tokens=["db", "host"],
            alternative_match_count=0,
            source_type=NodeType.ENV_VAR,        # Source is EnvVar
            target_type=NodeType.INFRA_RESOURCE  # Target is Infra
        )
        
        direction = next(r for r in res if r.penalty_type == PenaltyType.INVALID_DIRECTION)
        assert direction.multiplier < 1.0

    def test_evaluate_penalties_ambiguity(self, calculator):
        """Test AMBIGUITY penalty scales with count."""
        # 5 matches = high ambiguity
        res = calculator._evaluate_penalties(
            source_name="a", target_name="b", matched_tokens=[],
            alternative_match_count=5,
            source_type=None, target_type=None
        )
        ambig = next(r for r in res if r.penalty_type == PenaltyType.AMBIGUITY)
        # Should be significantly reduced
        assert ambig.multiplier < 0.5

    def test_calculate_base_score_case_insensitive(self, calculator):
        """Test score aggregation logic with case insensitivity."""
        # EXACT_MATCH checks source_name == target_name.
        # "PAYMENT_DB_HOST" != "payment_db_host".
        # But NORMALIZED_MATCH should apply (0.9).
        # And matched_tokens has 3 significant tokens -> HIGH OVERLAP (0.8).
        # Base score = max(0.9, 0.8) + bonus.
        
        result = calculator.calculate(
            "PAYMENT_DB_HOST", "payment_db_host",
            ["payment", "db", "host"], ["payment", "db", "host"],
            matched_tokens=["payment", "db", "host"]
        )
        # Should be high confidence, but not 1.0 because case mismatch
        assert result.score >= 0.9
        assert result.score <= 1.0

    def test_full_calculate_flow_generic_id(self, calculator):
        """Test end-to-end scoring for the 'id' problem."""
        result = calculator.calculate(
            source_name="id",
            target_name="id",
            source_tokens=["id"],
            target_tokens=["id"],
            source_type=NodeType.INFRA_RESOURCE,
            target_type=NodeType.ENV_VAR
        )
        
        # Even though signals are perfect (Exact Match = 1.0),
        # Penalties (Generic * Short * Common) should decimate it.
        # 1.0 * 0.1 (Generic) * 0.5 (Short) * 0.3 (Common) ≈ 0.015
        assert result.score < 0.2
        assert "generic_match" in result.explanation

    def test_explanation_formatting(self, calculator):
        """Test that explanation string is generated correctly."""
        result = calculator.calculate(
            "payment_api", "payment_api",
            ["payment", "api"], ["payment", "api"]
        )
        
        assert "Match: payment_api -> payment_api" in result.explanation
        assert "exact_match" in result.explanation
        assert "Final Score" in result.explanation

    def test_dictionaries_helpers(self, calculator):
        """Test internal helper for dict conversion."""
        # Using a valid penalty type from the updated Enum
        p = PenaltyResult(PenaltyType.SHORT_TOKEN, 0.5, "Too short")
        d = calculator._penalty_to_dict(p)
        assert d['penalty_type'] == 'short_token'
        assert d['multiplier'] == 0.5