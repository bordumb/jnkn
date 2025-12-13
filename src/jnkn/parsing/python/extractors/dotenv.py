"""
Python dotenv Environment Variable Extractor.

This module extracts environment variable references from Python code using
python-dotenv patterns:

- `dotenv_values()[\"VAR\"]`
- `config = dotenv_values(); config[\"VAR\"]`
- `config.get(\"VAR\")`

python-dotenv is a popular library for loading environment variables from
.env files, commonly used in web frameworks like Flask and Django.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name


class DotenvExtractor(BaseExtractor):
    """
    Extract environment variables from python-dotenv patterns.

    This extractor handles the dotenv library patterns for accessing
    environment variables loaded from .env files.

    Detected Patterns:
        - `dotenv_values()[\"VAR\"]` (inline access)
        - `config = dotenv_values(); config[\"VAR\"]` (dict access)
        - `config.get(\"VAR\")` (safe access with defaults)

    Example:
        ```python
        from dotenv import dotenv_values

        # All of these will be detected:
        config = dotenv_values()
        db_host = config[\"DATABASE_HOST\"]
        db_port = config.get(\"DATABASE_PORT\", \"5432\")
        ```
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "dotenv"

    @property
    def priority(self) -> int:
        """Return priority 70."""
        return 70

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains dotenv patterns.
        """
        return "dotenv" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Handles both inline dotenv_values() access and assignment-based
        patterns where the result is stored in a variable.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        # 1. Inline usage: dotenv_values()[\"VAR\"]
        inline_pattern = r'dotenv_values\s*\([^)]*\)\s*\[\s*["\']([^"\']+)["\']'
        for match in re.finditer(inline_pattern, ctx.text):
            yield from self._yield_match(match, 1, ctx, "dotenv_values")

        # 2. Assignment tracking: config = dotenv_values()
        assignment_pattern = r"(\w+)\s*=\s*dotenv_values\s*\("
        config_vars = set()
        for match in re.finditer(assignment_pattern, ctx.text):
            config_vars.add(match.group(1))

        if config_vars:
            vars_regex = "|".join(re.escape(v) for v in config_vars)

            # Dict subscript access: config[\"VAR\"]
            dict_access_pattern = rf'(?:{vars_regex})\s*\[\s*["\']([^"\']+)["\']'
            for match in re.finditer(dict_access_pattern, ctx.text):
                yield from self._yield_match(match, 1, ctx, "dotenv_values")

            # Safe get access: config.get(\"VAR\")
            get_access_pattern = rf'(?:{vars_regex})\.get\s*\(\s*["\']([^"\']+)["\']'
            for match in re.finditer(get_access_pattern, ctx.text):
                yield from self._yield_match(match, 1, ctx, "dotenv_values")

    def _yield_match(
        self,
        match: re.Match,
        group_idx: int,
        ctx: ExtractionContext,
        pattern_name: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        """
        Process a regex match and yield node/edge if valid.

        Args:
            match: The regex match object.
            group_idx: Which capture group contains the variable name.
            ctx: The extraction context.
            pattern_name: Name of the pattern for metadata.

        Yields:
            Node and Edge for valid environment variables.
        """
        var_name = match.group(group_idx)

        if not is_valid_env_var_name(var_name):
            return

        if not ctx.mark_seen(var_name):
            return

        line = ctx.get_line_number(match.start())

        # Use the context factory to create the node
        # This ensures `path` is always set correctly
        yield ctx.create_env_var_node(
            name=var_name,
            line=line,
            source="dotenv",
        )

        # Create the READS edge from file to env var
        yield ctx.create_reads_edge(
            target_id=f"env:{var_name}",
            line=line,
            pattern=pattern_name,
        )