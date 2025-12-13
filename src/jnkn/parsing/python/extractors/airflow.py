"""
Apache Airflow Variable Extractor.

This module extracts Airflow Variable references from Python code:

- `Variable.get(\"VAR\")`
- `Variable.get(\"VAR\", default_var=\"default\")`

Airflow Variables are key-value pairs stored in the Airflow metadata database,
commonly used for configuring DAGs with environment-specific values.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name


class AirflowExtractor(BaseExtractor):
    """
    Extract Airflow Variable references from Python code.

    This extractor handles Airflow's Variable.get() pattern for accessing
    configuration values stored in the Airflow metadata database.

    Detected Patterns:
        - `Variable.get(\"VAR\")`
        - `Variable.get(\"VAR\", default_var=\"default\")`

    Example:
        ```python
        from airflow.models import Variable

        # Both of these will be detected:
        api_key = Variable.get(\"API_KEY\")
        environment = Variable.get(\"ENVIRONMENT\", default_var=\"dev\")
        ```

    Note:
        This extractor only triggers if both "Variable" and "airflow" appear
        in the text, to avoid false positives on generic "Variable" classes.
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "airflow"

    @property
    def priority(self) -> int:
        """Return priority 50."""
        return 50

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains Airflow Variable patterns.
        """
        return "Variable" in ctx.text and "airflow" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract Airflow Variable nodes and edges.

        Uses regex to find Variable.get() patterns and yields properly
        constructed nodes with path set correctly.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected Airflow Variable.
            Edge: READS edges from the file to each variable.
        """
        # Pattern matches: Variable.get(\"VAR\")
        pattern = r'Variable\.get\s*\(\s*["\']([^"\']+)["\']'
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
                source="airflow_variable",
            )

            # Create the READS edge from file to env var
            yield ctx.create_reads_edge(
                target_id=f"env:{var_name}",
                line=line,
                pattern="airflow_variable",
            )