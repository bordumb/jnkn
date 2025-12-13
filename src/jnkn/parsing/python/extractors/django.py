"""
Django/django-environ Environment Variable Extractor.

This module extracts environment variable references from Python code using
django-environ patterns, commonly found in Django settings files:

- `env(\"VAR\")`
- `env.str(\"VAR\")`
- `env.bool(\"VAR\")`
- `env.int(\"VAR\")`
- And other typed accessors

django-environ is a popular Django app for managing environment variables
with 12-factor app methodology.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name


class DjangoExtractor(BaseExtractor):
    """
    Extract environment variables from django-environ patterns.

    This extractor handles the django-environ library patterns commonly
    used in Django settings files for configuration management.

    Detected Patterns:
        - `env(\"VAR\")`
        - `env.str(\"VAR\")`
        - `env.bool(\"VAR\")`
        - `env.int(\"VAR\")`
        - `env.float(\"VAR\")`
        - `env.list(\"VAR\")`
        - `env.dict(\"VAR\")`
        - `env.db(\"VAR\")`
        - `env.cache(\"VAR\")`
        - `env.url(\"VAR\")`

    Example:
        ```python
        import environ

        env = environ.Env(
            DEBUG=(bool, False),
        )

        # All of these will be detected:
        SECRET_KEY = env(\"SECRET_KEY\")
        DEBUG = env.bool(\"DEBUG\")
        DATABASE_URL = env.db(\"DATABASE_URL\")
        CACHE_URL = env.cache(\"CACHE_URL\")
        ```
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "django"

    @property
    def priority(self) -> int:
        """Return priority 60."""
        return 60

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text might contain django-environ patterns.
        """
        return "environ" in ctx.text or "Env" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Uses regex to find django-environ style accessor patterns and
        yields properly constructed nodes with path set correctly.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        # Pattern matches both:
        # - env(\"VAR\") - direct call
        # - env.TYPE(\"VAR\") - typed accessor
        pattern = r'env(?:\.[a-zA-Z_]+)?\s*\(\s*["\']([^"\']+)["\']'
        regex = re.compile(pattern)

        for match in regex.finditer(ctx.text):
            var_name = match.group(1)

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
                source="django_environ",
            )

            # Create the READS edge from file to env var
            yield ctx.create_reads_edge(
                target_id=f"env:{var_name}",
                line=line,
                pattern="django_environ",
            )