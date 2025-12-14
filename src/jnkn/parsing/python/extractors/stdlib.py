"""
Python Standard Library Environment Variable Extractor.

This module extracts environment variable references from Python code using
patterns from the standard library:

- `os.getenv("VAR")`
- `os.environ.get("VAR")`
- `os.environ["VAR"]`
- `environ.get("VAR")` (after `from os import environ`)
- `getenv("VAR")` (after `from os import getenv`)

This is the highest-priority Python extractor (100) as stdlib patterns
are the most common and reliable.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name

# Regex patterns for stdlib environment variable access
ENV_VAR_PATTERNS = [
    # os.getenv("VAR") or os.getenv('VAR')
    (r'os\.getenv\s*\(\s*["\']([^"\']+)["\']', "os.getenv"),
    # os.environ.get("VAR")
    (r'os\.environ\.get\s*\(\s*["\']([^"\']+)["\']', "os.environ.get"),
    # os.environ["VAR"]
    (r'os\.environ\s*\[\s*["\']([^"\']+)["\']', "os.environ[]"),
    # environ.get("VAR") - after from import
    (r'(?<!os\.)environ\.get\s*\(\s*["\']([^"\']+)["\']', "environ.get"),
    # environ["VAR"] - after from import
    (r'(?<!os\.)environ\s*\[\s*["\']([^"\']+)["\']', "environ[]"),
    # getenv("VAR") - after from import
    (r'(?<!os\.)getenv\s*\(\s*["\']([^"\']+)["\']', "getenv"),
]


class StdlibExtractor(BaseExtractor):
    """
    Extract environment variables from Python stdlib patterns.

    This extractor handles the most common Python patterns for accessing
    environment variables. It runs at priority 100 (highest) because
    stdlib patterns are unambiguous and should be processed first.

    Detected Patterns:
        - `os.getenv("VAR")` / `os.getenv('VAR')`
        - `os.environ.get("VAR")`
        - `os.environ["VAR"]`
        - `environ.get("VAR")` (after `from os import environ`)
        - `getenv("VAR")` (after `from os import getenv`)

    Example:
        ```python
        import os

        # All of these will be detected:
        db_host = os.getenv("DATABASE_HOST")
        db_port = os.environ.get("DATABASE_PORT", "5432")
        db_name = os.environ["DATABASE_NAME"]
        ```
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "stdlib"

    @property
    def priority(self) -> int:
        """Return priority 100 (highest for Python extractors)."""
        return 100

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains stdlib env patterns.
        """
        return "os." in ctx.text or "environ" in ctx.text or "getenv" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Uses regex patterns to find stdlib env var access patterns,
        validates the variable names, and yields properly constructed
        nodes with path set correctly.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        for pattern, pattern_name in ENV_VAR_PATTERNS:
            regex = re.compile(pattern)

            for match in regex.finditer(ctx.text):
                var_name = match.group(1)

                # Validate the variable name
                if not is_valid_env_var_name(var_name):
                    continue

                # Deduplicate using context's seen_ids
                if not ctx.mark_seen(var_name):
                    continue

                line = ctx.get_line_number(match.start())

                # Use the context factory to create the node
                # This ensures `path` is always set correctly
                yield ctx.create_env_var_node(
                    name=var_name,
                    line=line,
                    source=pattern_name,
                )

                # Create the READS edge from file to env var
                yield ctx.create_reads_edge(
                    target_id=f"env:{var_name}",
                    line=line,
                    pattern=pattern_name,
                )
