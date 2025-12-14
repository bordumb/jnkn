"""
Diff Analyzer - Compares dependency graphs between git refs.

This module provides the core diffing logic that compares two states
of a codebase and identifies what changed semantically.
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, List, Optional, Set

from ..core.graph import DependencyGraph
from ..core.types import Edge, Node, NodeType
from ..git.diff_engine import ChangedFile, FileStatus

logger = logging.getLogger(__name__)


class ChangeType(StrEnum):
    """Types of changes to nodes."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class NodeChange:
    """
    Represents a change to a single node in the dependency graph.

    This is the unified representation used throughout the diff pipeline.
    """

    node: Node
    change_type: ChangeType
    blast_radius: int = 0  # Number of downstream consumers
    details: Dict[str, Any] = field(default_factory=dict)

    # Convenience properties for templates
    @property
    def node_id(self) -> str:
        return self.node.id

    @property
    def name(self) -> str:
        return self.node.name

    @property
    def type(self) -> NodeType:
        return self.node.type

    @property
    def path(self) -> Optional[str]:
        return self.node.path

    @property
    def is_breaking(self) -> bool:
        """
        Determine if this change is potentially breaking.

        Breaking changes:
        - Removing infrastructure outputs
        - Removing environment variables that have consumers
        - Modifying infrastructure with high blast radius
        """
        if self.change_type == ChangeType.REMOVED:
            if self.node.type in (NodeType.INFRA_RESOURCE, NodeType.ENV_VAR):
                return True
            if self.blast_radius > 0:
                return True

        if self.change_type == ChangeType.MODIFIED:
            if self.node.type == NodeType.INFRA_RESOURCE and self.blast_radius > 5:
                return True

        return False

    @property
    def risk_indicator(self) -> str:
        """Get emoji risk indicator."""
        if self.is_breaking:
            return "🔴"
        if self.blast_radius > 5:
            return "🟠"
        if self.blast_radius > 0:
            return "🟡"
        return "🟢"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.type.value,
            "path": self.path,
            "change_type": self.change_type.value,
            "blast_radius": self.blast_radius,
            "is_breaking": self.is_breaking,
            "details": self.details,
        }


@dataclass
class EdgeChange:
    """Represents a change to an edge (dependency connection)."""

    source_id: str
    target_id: str
    change_type: ChangeType
    edge: Optional[Edge] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "change_type": self.change_type.value,
            "confidence": self.edge.confidence if self.edge else None,
        }


@dataclass
class DiffReport:
    """
    Complete diff report between two graph states.

    Provides both granular lists (added_nodes, removed_nodes, etc.)
    and a unified node_changes property for iteration.
    """

    base_ref: str
    head_ref: str

    # Granular node change lists
    added_nodes: List[NodeChange] = field(default_factory=list)
    removed_nodes: List[NodeChange] = field(default_factory=list)
    modified_nodes: List[NodeChange] = field(default_factory=list)

    # Edge changes
    added_edges: List[EdgeChange] = field(default_factory=list)
    removed_edges: List[EdgeChange] = field(default_factory=list)

    # Metadata
    files_changed: int = 0
    scan_duration_ms: float = 0

    @property
    def node_changes(self) -> List[NodeChange]:
        """
        Unified list of all node changes.

        Sorted by: removed first, then modified, then added.
        This is the primary iteration property used by formatters.
        """
        all_changes = self.removed_nodes + self.modified_nodes + self.added_nodes
        return all_changes

    @property
    def edge_changes(self) -> List[EdgeChange]:
        """Unified list of all edge changes."""
        return self.removed_edges + self.added_edges

    @property
    def total_changes(self) -> int:
        return len(self.node_changes)

    @property
    def breaking_changes(self) -> List[NodeChange]:
        """Get all potentially breaking changes."""
        return [c for c in self.node_changes if c.is_breaking]

    @property
    def has_infra_changes(self) -> bool:
        """Check if any infrastructure was modified."""
        return any(c.type == NodeType.INFRA_RESOURCE for c in self.node_changes)

    @property
    def has_breaking_changes(self) -> bool:
        return len(self.breaking_changes) > 0

    def get_changes_by_type(self, node_type: NodeType) -> List[NodeChange]:
        """Get all changes for a specific node type."""
        return [c for c in self.node_changes if c.type == node_type]

    def get_affected_paths(self) -> Set[str]:
        """Get all file paths affected by changes."""
        paths = set()
        for change in self.node_changes:
            if change.path:
                paths.add(change.path)
        return paths

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_ref": self.base_ref,
            "head_ref": self.head_ref,
            "summary": {
                "total_changes": self.total_changes,
                "added": len(self.added_nodes),
                "removed": len(self.removed_nodes),
                "modified": len(self.modified_nodes),
                "breaking_changes": len(self.breaking_changes),
                "has_infra_changes": self.has_infra_changes,
                "files_changed": self.files_changed,
            },
            "changes": [c.to_dict() for c in self.node_changes],
            "edge_changes": [e.to_dict() for e in self.edge_changes],
        }


class DiffAnalyzer:
    """
    Analyzes differences between two dependency graphs.

    Supports two modes:
    1. Full graph comparison (when both graphs are available)
    2. File-based inference (when only changed files are known)
    """

    def __init__(self, graph: Optional[DependencyGraph] = None):
        """
        Initialize the analyzer.

        Args:
            graph: The current (HEAD) dependency graph for blast radius lookups
        """
        self.graph = graph

    def compare(
        self,
        base_graph: DependencyGraph,
        head_graph: DependencyGraph,
        base_ref: str = "base",
        head_ref: str = "HEAD",
    ) -> DiffReport:
        """
        Compare two complete graphs.

        This is the most accurate method but requires both graphs to be built.
        """
        report = DiffReport(base_ref=base_ref, head_ref=head_ref)

        # Index nodes by ID
        base_nodes = {n.id: n for n in base_graph.iter_nodes()}
        head_nodes = {n.id: n for n in head_graph.iter_nodes()}

        base_ids = set(base_nodes.keys())
        head_ids = set(head_nodes.keys())

        # Added nodes (in head but not in base)
        for node_id in head_ids - base_ids:
            node = head_nodes[node_id]
            blast_radius = self._calculate_blast_radius(head_graph, node_id)
            report.added_nodes.append(
                NodeChange(
                    node=node,
                    change_type=ChangeType.ADDED,
                    blast_radius=blast_radius,
                )
            )

        # Removed nodes (in base but not in head)
        for node_id in base_ids - head_ids:
            node = base_nodes[node_id]
            # For removed nodes, blast radius is from base graph
            blast_radius = self._calculate_blast_radius(base_graph, node_id)
            report.removed_nodes.append(
                NodeChange(
                    node=node,
                    change_type=ChangeType.REMOVED,
                    blast_radius=blast_radius,
                )
            )

        # Modified nodes (in both, check for changes)
        for node_id in base_ids & head_ids:
            base_node = base_nodes[node_id]
            head_node = head_nodes[node_id]

            if self._node_changed(base_node, head_node):
                blast_radius = self._calculate_blast_radius(head_graph, node_id)
                report.modified_nodes.append(
                    NodeChange(
                        node=head_node,
                        change_type=ChangeType.MODIFIED,
                        blast_radius=blast_radius,
                        details=self._get_change_details(base_node, head_node),
                    )
                )

        # Compare edges
        self._compare_edges(base_graph, head_graph, report)

        # Count unique files
        report.files_changed = len(report.get_affected_paths())

        return report

    def analyze_from_changed_files(
        self,
        graph: DependencyGraph,
        changed_files: List[ChangedFile],
        base_ref: str = "base",
        head_ref: str = "HEAD",
    ) -> DiffReport:
        """
        Create a diff report based on git-reported changed files.

        This is used when we can't build a base graph (faster, less accurate).
        We infer changes based on which files changed and what nodes are in them.

        Args:
            graph: The current (HEAD) dependency graph
            changed_files: List of ChangedFile from GitDiffEngine
            base_ref: Name of base reference
            head_ref: Name of head reference
        """
        report = DiffReport(base_ref=base_ref, head_ref=head_ref)
        report.files_changed = len(changed_files)

        # Build path index
        path_to_status: Dict[str, FileStatus] = {}
        for cf in changed_files:
            # Normalize path
            normalized = str(cf.path).lstrip("./")
            path_to_status[normalized] = cf.status

            # Also index old path for renames
            if cf.old_path:
                path_to_status[str(cf.old_path).lstrip("./")] = FileStatus.DELETED

        # Find nodes in changed files
        for node in graph.iter_nodes():
            if not node.path:
                continue

            node_path = str(node.path).lstrip("./")

            if node_path in path_to_status:
                status = path_to_status[node_path]
                blast_radius = self._calculate_blast_radius(graph, node.id)

                if status == FileStatus.ADDED:
                    report.added_nodes.append(
                        NodeChange(
                            node=node,
                            change_type=ChangeType.ADDED,
                            blast_radius=blast_radius,
                        )
                    )
                elif status == FileStatus.DELETED:
                    report.removed_nodes.append(
                        NodeChange(
                            node=node,
                            change_type=ChangeType.REMOVED,
                            blast_radius=blast_radius,
                        )
                    )
                else:  # MODIFIED, RENAMED, etc.
                    report.modified_nodes.append(
                        NodeChange(
                            node=node,
                            change_type=ChangeType.MODIFIED,
                            blast_radius=blast_radius,
                        )
                    )

        return report

    def _calculate_blast_radius(self, graph: DependencyGraph, node_id: str) -> int:
        """Calculate how many nodes are downstream of this node."""
        try:
            descendants = graph.get_descendants(node_id)
            return len(descendants)
        except Exception as e:
            logger.warning(f"Failed to calculate blast radius for {node_id}: {e}")
            return 0

    def _node_changed(self, base: Node, head: Node) -> bool:
        """Determine if a node's content changed."""
        # Check content hash if available
        base_hash = base.metadata.get("content_hash")
        head_hash = head.metadata.get("content_hash")

        if base_hash and head_hash:
            return base_hash != head_hash

        # Fall back to token comparison
        if set(base.tokens or []) != set(head.tokens or []):
            return True

        # Check line number changes
        # Use getattr to safely check for 'line' since it might be dynamic or missing
        base_line = getattr(base, "line", base.metadata.get("line"))
        head_line = getattr(head, "line", head.metadata.get("line"))

        if base_line != head_line:
            return True

        return False

    def _get_change_details(self, base: Node, head: Node) -> Dict[str, Any]:
        """Get details about what changed."""
        details = {}

        base_tokens = set(base.tokens or [])
        head_tokens = set(head.tokens or [])

        added = head_tokens - base_tokens
        removed = base_tokens - head_tokens

        if added:
            details["added_tokens"] = list(added)
        if removed:
            details["removed_tokens"] = list(removed)

        base_line = getattr(base, "line", base.metadata.get("line"))
        head_line = getattr(head, "line", head.metadata.get("line"))

        if base_line != head_line:
            details["line_moved"] = {"from": base_line, "to": head_line}

        return details

    def _compare_edges(
        self,
        base_graph: DependencyGraph,
        head_graph: DependencyGraph,
        report: DiffReport,
    ) -> None:
        """Compare edges between graphs."""
        # Include edge type in the key to detect relationship changes
        base_edges = {(e.source_id, e.target_id, e.type): e for e in base_graph.iter_edges()}
        head_edges = {(e.source_id, e.target_id, e.type): e for e in head_graph.iter_edges()}

        # Added edges
        for key in set(head_edges.keys()) - set(base_edges.keys()):
            report.added_edges.append(
                EdgeChange(
                    source_id=key[0],
                    target_id=key[1],
                    change_type=ChangeType.ADDED,
                    edge=head_edges[key],
                )
            )

        # Removed edges
        for key in set(base_edges.keys()) - set(head_edges.keys()):
            report.removed_edges.append(
                EdgeChange(
                    source_id=key[0],
                    target_id=key[1],
                    change_type=ChangeType.REMOVED,
                    edge=base_edges[key],
                )
            )
