"""
Heuristic Environment Variable Extractor.

This module provides a fallback extractor that uses heuristics to detect
likely environment variable references that might be missed by other
pattern-specific extractors:

- `DATABASE_URL = env.get(...)` where the constant name looks like an env var
- Pattern-based detection for common env var naming conventions

This runs at the lowest priority (10) to avoid interfering with more
specific extractors.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, NodeType, RelationshipType
from ...base import BaseExtractor, ExtractionContext


class HeuristicExtractor(BaseExtractor):
    """
    Heuristic fallback extractor for environment variables.

    This extractor uses pattern matching on assignment statements to find
    likely environment variable references that weren't caught by
    framework-specific extractors.

    Detection Strategy:
        1. Find UPPER_CASE constant assignments
        2. Check if the constant name ends with common env var suffixes
        3. Verify the right-hand side contains env-related keywords
        4. Mark matches with lower confidence (0.7)

    Recognized Suffixes:
        - `_URL`, `_HOST`, `_PORT`, `_KEY`, `_SECRET`
        - `_TOKEN`, `_PASSWORD`, `_USER`, `_PATH`
        - `_DIR`, `_ENDPOINT`, `_URI`, `_DSN`, `_CONN`

    Example:
        ```python
        # This will be detected (ends with _URL, contains env-like RHS)
        DATABASE_URL = config.get(\"database_url\")

        # This will be detected (ends with _HOST, contains settings)
        REDIS_HOST = settings.REDIS_HOST
        ```

    Note:
        Results from this extractor have `confidence: 0.7` in metadata
        to indicate they are heuristic matches.
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "heuristic"

    @property
    def priority(self) -> int:
        """Return priority 10 (lowest, runs last)."""
        return 10

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Always return True - heuristic runs on all files.

        Args:
            ctx: The extraction context.

        Returns:
            bool: Always True.
        """
        return True

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variables using heuristics.

        Searches for UPPER_CASE assignments with env-related suffixes
        that also have env-like indicators on the right-hand side.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for detected variables (with confidence: 0.7).
            Edge: READS edges from the file to each env var.
        """
        # Pattern: UPPER_CASE_NAME = ... at line start
        # Captures env var-like constant names with common suffixes
        env_like_assignment = re.compile(
            r"^([A-Z][A-Z0-9_]*(?:_URL|_HOST|_PORT|_KEY|_SECRET|_TOKEN|_PASSWORD|"
            r"_USER|_PATH|_DIR|_ENDPOINT|_URI|_DSN|_CONN))\s*=",
            re.MULTILINE,
        )

        # Keywords that indicate env-related context on RHS
        env_indicators = [
            "os.getenv",
            "os.environ",
            "getenv",
            "environ",
            "config",
            "settings",
            "env",
            "ENV",
        ]

        for match in env_like_assignment.finditer(ctx.text):
            var_name = match.group(1)

            # Already seen by a more specific extractor
            if not ctx.mark_seen(var_name):
                continue

            # Get the full line to check for env indicators
            line_start = ctx.text.rfind("\n", 0, match.start()) + 1
            line_end = ctx.text.find("\n", match.end())
            if line_end == -1:
                line_end = len(ctx.text)
            line_content = ctx.text[line_start:line_end]

            # Verify env-related context on right-hand side
            if not any(ind in line_content for ind in env_indicators):
                continue

            line = ctx.get_line_number(match.start())

            # Use context factory with heuristic-specific metadata
            yield ctx.create_env_var_node(
                name=var_name,
                line=line,
                source="heuristic",
                extra_metadata={"confidence": 0.7},
            )

            yield ctx.create_reads_edge(
                target_id=f"env:{var_name}",
                line=line,
                pattern="heuristic",
            )