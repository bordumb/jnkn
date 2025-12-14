"""
Risk Analysis Engine.

Calculates Change Safety Score (0-100) and Risk Level based on:
1. Blast radius of changed nodes
2. Type of artifacts changed (infra > config > code)
3. Nature of change (deletion > modification > addition)
4. Cross-domain impact
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import List, Optional, Tuple

from ..core.types import NodeType
from .diff_analyzer import ChangeType, DiffReport, NodeChange

logger = logging.getLogger(__name__)


class RiskLevel(StrEnum):
    """Risk level categories."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RiskFactor:
    """A factor contributing to the risk score."""

    name: str
    description: str
    score_impact: int  # Points deducted from 100
    severity: RiskLevel
    node_id: Optional[str] = None

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "score_impact": self.score_impact,
            "severity": self.severity.value,
            "node_id": self.node_id,
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment for a change."""

    score: int  # 0-100 (100 = safest)
    level: RiskLevel
    factors: List[RiskFactor] = field(default_factory=list)
    summary: str = ""

    @property
    def icon(self) -> str:
        return {
            RiskLevel.CRITICAL: "🔴",
            RiskLevel.HIGH: "🟠",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.LOW: "🟢",
        }.get(self.level, "⚪")

    @property
    def color(self) -> str:
        return {
            RiskLevel.CRITICAL: "red",
            RiskLevel.HIGH: "orange1",
            RiskLevel.MEDIUM: "yellow",
            RiskLevel.LOW: "green",
        }.get(self.level, "white")

    def to_dict(self):
        return {
            "score": self.score,
            "level": self.level.value,
            "factors": [f.to_dict() for f in self.factors],
            "summary": self.summary,
        }


class RiskAnalyzer:
    """
    Analyzes risk from a DiffReport.

    Scoring approach:
    - Start at 100 (perfect safety)
    - Deduct points for each risk factor
    - Cap at 0 (maximum risk)
    """

    # Base penalties by artifact type and change type
    PENALTIES = {
        # (NodeType, ChangeType) -> base penalty
        (NodeType.INFRA_RESOURCE, ChangeType.REMOVED): 40,
        (NodeType.INFRA_RESOURCE, ChangeType.MODIFIED): 25,
        (NodeType.INFRA_RESOURCE, ChangeType.ADDED): 5,
        (NodeType.ENV_VAR, ChangeType.REMOVED): 30,
        (NodeType.ENV_VAR, ChangeType.MODIFIED): 15,
        (NodeType.ENV_VAR, ChangeType.ADDED): 3,
        (NodeType.CONFIG_KEY, ChangeType.REMOVED): 20,
        (NodeType.CONFIG_KEY, ChangeType.MODIFIED): 10,
        (NodeType.CONFIG_KEY, ChangeType.ADDED): 2,
        # Default for other types (Code Entities / Functions / Classes)
        (NodeType.CODE_ENTITY, ChangeType.REMOVED): 10,
        (NodeType.CODE_ENTITY, ChangeType.MODIFIED): 5,
        (NodeType.CODE_ENTITY, ChangeType.ADDED): 1,
    }

    # Blast radius multipliers
    BLAST_RADIUS_THRESHOLDS = [
        (50, 2.0, RiskLevel.CRITICAL),  # 50+ consumers = 2x penalty, critical
        (20, 1.5, RiskLevel.HIGH),  # 20+ consumers = 1.5x penalty, high
        (5, 1.2, RiskLevel.MEDIUM),  # 5+ consumers = 1.2x penalty, medium
        (0, 1.0, RiskLevel.LOW),  # default
    ]

    def analyze(self, diff_report: DiffReport) -> RiskAssessment:
        """
        Analyze a diff report and produce a risk assessment.
        """
        score = 100
        factors: List[RiskFactor] = []

        for change in diff_report.node_changes:
            penalty, factor = self._assess_change(change)

            if penalty > 0:
                score -= penalty
                factors.append(factor)

        # Bonus penalty for having breaking changes
        breaking_count = len(diff_report.breaking_changes)
        if breaking_count > 0:
            breaking_penalty = min(20, breaking_count * 5)
            score -= breaking_penalty
            factors.append(
                RiskFactor(
                    name="breaking_changes",
                    description=f"{breaking_count} potentially breaking change(s)",
                    score_impact=breaking_penalty,
                    severity=RiskLevel.HIGH,
                )
            )

        # Normalize score
        score = max(0, min(100, score))

        # Determine level
        level = self._score_to_level(score)

        # Generate summary
        summary = self._generate_summary(diff_report, factors, score)

        return RiskAssessment(
            score=score,
            level=level,
            factors=factors,
            summary=summary,
        )

    def _assess_change(self, change: NodeChange) -> Tuple[int, RiskFactor]:
        """Assess risk for a single change."""
        # Get base penalty
        key = (change.type, change.change_type)
        base_penalty = self.PENALTIES.get(key, 5)

        # Apply blast radius multiplier
        multiplier = 1.0
        severity = RiskLevel.LOW

        for threshold, mult, sev in self.BLAST_RADIUS_THRESHOLDS:
            if change.blast_radius >= threshold:
                multiplier = mult
                severity = sev
                break

        final_penalty = int(base_penalty * multiplier)

        # Build description
        description = f"{change.change_type.value.title()} {change.type.value}: {change.name}"
        if change.blast_radius > 0:
            description += f" ({change.blast_radius} downstream consumers)"

        factor = RiskFactor(
            name=f"{change.type.value}_{change.change_type.value}",
            description=description,
            score_impact=final_penalty,
            severity=severity,
            node_id=change.node_id,
        )

        return final_penalty, factor

    def _score_to_level(self, score: int) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score < 40:
            return RiskLevel.CRITICAL
        elif score < 60:
            return RiskLevel.HIGH
        elif score < 80:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_summary(
        self, diff_report: DiffReport, factors: List[RiskFactor], score: int
    ) -> str:
        """Generate human-readable summary."""
        if score >= 90:
            return "Low risk changes with minimal downstream impact."

        # Get top factors
        sorted_factors = sorted(factors, key=lambda f: f.score_impact, reverse=True)
        top = sorted_factors[:2]

        parts = []

        if diff_report.has_infra_changes:
            parts.append("infrastructure modifications")

        breaking = len(diff_report.breaking_changes)
        if breaking > 0:
            parts.append(f"{breaking} potentially breaking change(s)")

        high_blast = [c for c in diff_report.node_changes if c.blast_radius > 5]
        if high_blast:
            parts.append(f"{len(high_blast)} change(s) with significant blast radius")

        if parts:
            return "Risk factors: " + ", ".join(parts) + "."

        return f"Score impacted by: {top[0].description}" if top else ""
