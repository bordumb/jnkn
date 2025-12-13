"""
Java Environment Variable Extractor.

This module extracts environment variable reads and property injections
from Java source code:

- `System.getenv("VAR")`
- `System.getProperty("prop")`
- Spring `@Value("${VAR}")` annotation
- Spring `Environment.getProperty("VAR")`

All nodes are created with proper `path` fields to enable "Open in Editor"
functionality in the visualization.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, NodeType, RelationshipType
from ...base import ExtractionContext


class JavaEnvVarExtractor:
    """
    Extract environment variable reads and property injections from Java code.

    This extractor handles Java stdlib patterns and Spring Framework
    configuration patterns.

    Detected Patterns:
        - `System.getenv("VAR")`
        - `System.getProperty("prop")`
        - `@Value("${VAR}")` / `@Value("${VAR:default}")`
        - `environment.getProperty("VAR")`

    Example:
        ```java
        public class MyConfig {
            // System patterns
            String dbHost = System.getenv("DATABASE_HOST");
            String javaHome = System.getProperty("java.home");

            // Spring patterns
            @Value("${API_KEY}")
            private String apiKey;

            @Value("${DEBUG:false}")
            private boolean debug;

            public void init(Environment env) {
                String port = env.getProperty("SERVER_PORT");
            }
        }
        ```
    """

    name = "java_env_vars"
    priority = 100

    # System.getenv("VAR")
    GETENV = re.compile(r'System\.getenv\s*\(\s*"([^"]+)"\s*\)')

    # System.getProperty("prop")
    GETPROP = re.compile(r'System\.getProperty\s*\(\s*"([^"]+)"\s*\)')

    # @Value("${VAR}") or @Value("${VAR:default}")
    SPRING_VALUE = re.compile(r'@Value\s*\(\s*"\$\{\s*([^}]+)\s*\}"\s*\)')

    # environment.getProperty("prop") - common variable name for Environment
    SPRING_ENV = re.compile(r'(?:env|environment)\.getProperty\s*\(\s*"([^"]+)"\s*\)')

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains Java env patterns.
        """
        return "System.get" in ctx.text or "@Value" in ctx.text or "getProperty" in ctx.text

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
            (self.GETENV, "System.getenv"),
            (self.GETPROP, "System.getProperty"),
            (self.SPRING_VALUE, "spring_value_annotation"),
            (self.SPRING_ENV, "spring_environment"),
        ]:
            for match in pattern.finditer(ctx.text):
                raw_var = match.group(1).strip()

                # Handle Spring placeholders with defaults: ${VAR:default}
                if ":" in raw_var:
                    var_name = raw_var.split(":", 1)[0].strip()
                    default_value = raw_var.split(":", 1)[1].strip()
                else:
                    var_name = raw_var
                    default_value = None

                # Validate variable name
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
                        "default_value": default_value,
                    },
                )

                yield Edge(
                    source_id=ctx.file_id,
                    target_id=env_id,
                    type=RelationshipType.READS,
                    metadata={"pattern": source},
                )