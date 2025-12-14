"""
Go Environment Variable Extractor.

This module extracts environment variable reads from Go source code:

- `os.Getenv("VAR")`
- `os.LookupEnv("VAR")`
- `syscall.Getenv("VAR")`
- `viper.GetString("key")` (config keys that often map to env vars)

All nodes are created with proper `path` fields to enable "Open in Editor"
functionality in the visualization.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, NodeType, RelationshipType
from ...base import ExtractionContext


class GoEnvVarExtractor:
    """
    Extract environment variable reads from Go code.

    This extractor handles the most common Go patterns for accessing
    environment variables, including both stdlib and viper.

    Detected Patterns:
        - `os.Getenv("VAR")`
        - `os.LookupEnv("VAR")`
        - `syscall.Getenv("VAR")`
        - `viper.GetString("key")` / `viper.GetInt("key")` / etc.

    Example:
        ```go
        package main

        import "os"

        func main() {
            // All of these will be detected:
            dbHost := os.Getenv("DATABASE_HOST")
            dbPort, ok := os.LookupEnv("DATABASE_PORT")
            apiKey := viper.GetString("api_key")
        }
        ```

    Note:
        Viper keys are often lowercase but may map to UPPERCASE env vars.
        The stitcher logic may need to handle case normalization.
    """

    name = "go_env_vars"
    priority = 100

    # os.Getenv("VAR") or syscall.Getenv("VAR")
    GETENV = re.compile(r'(?:os|syscall)\.Getenv\s*\(\s*"([^"]+)"\s*\)')

    # os.LookupEnv("VAR")
    LOOKUPENV = re.compile(r'os\.LookupEnv\s*\(\s*"([^"]+)"\s*\)')

    # viper.GetString("key") - commonly used for config which can be env vars
    VIPER = re.compile(r'viper\.Get(?:String|Int|Bool|Float64|Duration)\s*\(\s*"([^"]+)"\s*\)')

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains Go env patterns.
        """
        return "os." in ctx.text or "syscall." in ctx.text or "viper." in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        seen = set()

        for pattern, source in [
            (self.GETENV, "os.Getenv"),
            (self.LOOKUPENV, "os.LookupEnv"),
            (self.VIPER, "viper"),
        ]:
            for match in pattern.finditer(ctx.text):
                var_name = match.group(1)

                # Basic validation
                if not var_name or " " in var_name:
                    continue

                if var_name in seen:
                    continue
                seen.add(var_name)

                line = ctx.get_line_number(match.start())
                env_id = f"env:{var_name}"

                # CRITICAL: Always set path for "Open in Editor" functionality
                yield Node(
                    id=env_id,
                    name=var_name,
                    type=NodeType.ENV_VAR,
                    path=str(ctx.file_path),
                    metadata={
                        "source": source,
                        "line": line,
                        "is_config_key": source == "viper",
                    },
                )

                yield Edge(
                    source_id=ctx.file_id,
                    target_id=env_id,
                    type=RelationshipType.READS,
                    metadata={"pattern": source},
                )
