"""
Click and Typer Environment Variable Extractor.

This module extracts environment variable references from Click and Typer
command-line argument decorators:

- `@click.option(..., envvar=\"VAR\")`
- `@click.option(..., envvar=[\"VAR1\", \"VAR2\"])`
- `typer.Option(..., envvar=\"VAR\")`

Click and Typer are popular Python CLI frameworks that support binding
command-line options to environment variables.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name


class ClickTyperExtractor(BaseExtractor):
    """
    Extract environment variables from Click/Typer decorators.

    This extractor handles the envvar parameter in Click and Typer
    option decorators, which bind CLI options to environment variables.

    Detected Patterns:
        - `@click.option(\"--name\", envvar=\"VAR\")`
        - `@click.option(\"--name\", envvar=[\"VAR1\", \"VAR2\"])`
        - `typer.Option(..., envvar=\"VAR\")`

    Example:
        ```python
        import click

        @click.command()
        @click.option(\"--host\", envvar=\"API_HOST\", default=\"localhost\")
        @click.option(\"--port\", envvar=[\"API_PORT\", \"PORT\"], default=8080)
        def serve(host, port):
            pass
        ```

        ```python
        import typer

        def main(
            host: str = typer.Option(\"localhost\", envvar=\"API_HOST\"),
        ):
            pass
        ```
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "click_typer"

    @property
    def priority(self) -> int:
        """Return priority 80."""
        return 80

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains Click or Typer patterns.
        """
        return "click" in ctx.text or "typer" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Uses regex to find Click/Typer envvar parameters and yields
        properly constructed nodes with path set correctly.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        # Pattern matches both string and list values for envvar:
        # envvar=\"VAR\" or envvar=[\"VAR1\", \"VAR2\"]
        click_pattern = re.compile(
            r'(?:@click\.option|typer\.Option)\s*\([^)]*envvar\s*=\s*'
            r'(\[[^\]]+\]|["\'][^"\']+["\'])',
            re.DOTALL,
        )

        for match in click_pattern.finditer(ctx.text):
            envvar_val = match.group(1)
            line = ctx.get_line_number(match.start())

            # Extract all string values from the envvar parameter
            vars_found = re.findall(r'["\']([^"\']+)["\']', envvar_val)

            for var_name in vars_found:
                if not is_valid_env_var_name(var_name):
                    continue

                if not ctx.mark_seen(var_name):
                    continue

                # Use the context factory to create the node
                # This ensures `path` is always set correctly
                yield ctx.create_env_var_node(
                    name=var_name,
                    line=line,
                    source="click_typer",
                )

                # Create the READS edge from file to env var
                yield ctx.create_reads_edge(
                    target_id=f"env:{var_name}",
                    line=line,
                    pattern="click_typer",
                )