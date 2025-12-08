"""
Core modules for Junkan.

This package contains the fundamental building blocks:
- types: Data structures (Node, Edge, etc.)
- graph: In-memory dependency graph
- stitching: Cross-domain dependency discovery
- storage: Persistence adapters
"""

from .types import (
    Node, Edge, NodeType, RelationshipType,
    MatchStrategy, MatchResult, ScanMetadata
)
from .graph import DependencyGraph, TokenIndex
from .stitching import Stitcher, StitchingRule, MatchConfig

__all__ = [
    "Node", "Edge", "NodeType", "RelationshipType",
    "MatchStrategy", "MatchResult", "ScanMetadata",
    "DependencyGraph", "TokenIndex",
    "Stitcher", "StitchingRule", "MatchConfig",
]