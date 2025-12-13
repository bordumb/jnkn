"""
Python environs Library Environment Variable Extractor.

This module extracts environment variable references from Python code using
the environs library patterns:

- `env.str(\"VAR\")`
- `env.int(\"VAR\")`
- `env.bool(\"VAR\")`
- `env.list(\"VAR\")`
- And other typed accessors

The environs library is a typed wrapper around os.environ that provides
schema validation and type coercion, popular in Flask and other frameworks.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name


class EnvironsExtractor(BaseExtractor):
    """
    Extract environment variables from environs library patterns.

    This extractor handles the environs library's typed accessor patterns
    for environment variables with validation and type coercion.

    Detected Patterns:
        - `env.str(\"VAR\")`
        - `env.int(\"VAR\")`
        - `env.bool(\"VAR\")`
        - `env.float(\"VAR\")`
        - `env.list(\"VAR\")`
        - `env.dict(\"VAR\")`
        - `env.json(\"VAR\")`
        - `env.url(\"VAR\")`
        - `env.path(\"VAR\")`
        - `env.db(\"VAR\")`
        - `env.cache(\"VAR\")`
        - `env.email_url(\"VAR\")`
        - `env.search_url(\"VAR\")`

    Example:
        ```python
        from environs import Env

        env = Env()
        env.read_env()

        # All of these will be detected:
        DEBUG = env.bool(\"DEBUG\", default=False)
        DATABASE_URL = env.str(\"DATABASE_URL\")
        MAX_CONNECTIONS = env.int(\"MAX_CONNECTIONS\", default=10)
        ```
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "environs"

    @property
    def priority(self) -> int:
        """Return priority 40."""
        return 40

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text might contain environs patterns.
        """
        return "env" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Uses regex to find environs-style typed accessor patterns and
        yields properly constructed nodes with path set correctly.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        # Pattern matches: env.TYPE(\"VAR\")
        # Where TYPE is one of the supported accessor methods
        pattern = (
            r'env\.(str|int|bool|float|list|dict|json|url|path|db|cache|email_url|search_url)'
            r'\s*\(\s*["\']([^"\']+)["\']'
        )
        regex = re.compile(pattern)

        for match in regex.finditer(ctx.text):
            var_name = match.group(2)

            if not is_valid_env_var_name(var_name):
                continue

            if not ctx.mark_seen(var_name):
                continue

            line = ctx.get_line_number(match.start())

            # Use the context factory to create the node
            # This ensures `path` is always set correctly
            yield ctx.create_env_var_node(
                name=var_name,
                line=line,
                source="environs",
            )

            # Create the READS edge from file to env var
            yield ctx.create_reads_edge(
                target_id=f"env:{var_name}",
                line=line,
                pattern="environs",
            )