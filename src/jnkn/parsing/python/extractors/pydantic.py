"""
Pydantic Settings Environment Variable Extractor.

This module extracts environment variable references from Pydantic BaseSettings
classes and Field declarations:

- `Field(env=\"VAR\")` - explicit env var binding
- `class Settings(BaseSettings): field: str` - implicit env var from field name
- `env_prefix = \"APP_\"` - prefixed env var names

Pydantic Settings is a popular way to manage application configuration with
type validation and environment variable binding.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import BaseExtractor, ExtractionContext
from ..validation import is_valid_env_var_name


class PydanticExtractor(BaseExtractor):
    """
    Extract environment variables from Pydantic Settings classes.

    This extractor handles Pydantic's BaseSettings pattern where
    class fields are automatically bound to environment variables.

    Detected Patterns:
        - `Field(env=\"VAR\")` - explicit env var binding
        - `class Settings(BaseSettings): field: str` - inferred from field name
        - `env_prefix = \"APP_\"` - prefixes applied to all fields

    Example:
        ```python
        from pydantic import BaseSettings, Field

        class Settings(BaseSettings):
            # Explicit binding
            api_key: str = Field(env=\"API_KEY\")

            # Inferred: DATABASE_URL (uppercase of field name)
            database_url: str

            # With prefix (if class has env_prefix = \"APP_\")
            # Results in: APP_DEBUG
            debug: bool = False

            class Config:
                env_prefix = \"APP_\"
        ```
    """

    @property
    def name(self) -> str:
        """Return the unique identifier for this extractor."""
        return "pydantic"

    @property
    def priority(self) -> int:
        """Return priority 90."""
        return 90

    def can_extract(self, ctx: ExtractionContext) -> bool:
        """
        Check if this extractor should run on the given context.

        Args:
            ctx: The extraction context.

        Returns:
            bool: True if the text contains Pydantic patterns.
        """
        return "BaseSettings" in ctx.text or "Field" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        """
        Extract environment variable nodes and edges.

        Handles both explicit Field(env=...) bindings and implicit
        env var names inferred from BaseSettings class fields.

        Args:
            ctx: The extraction context containing file info and text.

        Yields:
            Node: ENV_VAR nodes for each detected environment variable.
            Edge: READS edges from the file to each env var.
        """
        # 1. Explicit Field(env=\"VAR\") pattern
        yield from self._extract_field_env(ctx)

        # 2. Implicit env vars from BaseSettings class fields
        yield from self._extract_basesettings_fields(ctx)

    def _extract_field_env(
        self, ctx: ExtractionContext
    ) -> Generator[Union[Node, Edge], None, None]:
        """Extract explicit Field(env=\"VAR\") patterns."""
        field_env_pattern = r'Field\s*\([^)]*env\s*=\s*["\']([^"\']+)["\']'
        regex = re.compile(field_env_pattern, re.DOTALL)

        for match in regex.finditer(ctx.text):
            var_name = match.group(1)

            if not is_valid_env_var_name(var_name):
                continue

            if not ctx.mark_seen(var_name):
                continue

            line = ctx.get_line_number(match.start())

            yield ctx.create_env_var_node(
                name=var_name,
                line=line,
                source="pydantic_field",
            )

            yield ctx.create_reads_edge(
                target_id=f"env:{var_name}",
                line=line,
                pattern="pydantic_field",
            )

    def _extract_basesettings_fields(
        self, ctx: ExtractionContext
    ) -> Generator[Union[Node, Edge], None, None]:
        """Extract implicit env vars from BaseSettings class fields."""
        # Find BaseSettings classes with their body
        class_pattern = re.compile(
            r"class\s+(\w+)\s*\([^)]*BaseSettings[^)]*\)\s*:\s*\n(.*?)"
            r"(?=\nclass\s+\w+\s*[\(:]|\Z)",
            re.DOTALL,
        )

        for class_match in class_pattern.finditer(ctx.text):
            class_name = class_match.group(1)
            class_body = class_match.group(2)
            class_start_line = ctx.get_line_number(class_match.start())

            # Check for env_prefix in Config
            prefix = ""
            prefix_match = re.search(
                r'class\s+Config\s*:.*?env_prefix\s*=\s*["\']([^"\']*)["\']',
                class_body,
                re.DOTALL,
            )
            if prefix_match:
                prefix = prefix_match.group(1)

            # Find field definitions: field_name: Type
            # Uses 4-space indentation to find class-level fields
            field_pattern = re.compile(r"^([ \t]{4}(\w+)\s*:\s*\w+.*?)$", re.MULTILINE)

            for field_match in field_pattern.finditer(class_body):
                field_line_content = field_match.group(1)
                field_name = field_match.group(2)

                # Skip private fields and Config class
                if field_name.startswith("_") or field_name == "Config":
                    continue

                # Skip if Field(env=...) is already present (handled above)
                if "Field" in field_line_content and "env=" in field_line_content:
                    continue

                # Construct env var name: PREFIX + UPPERCASE_FIELD_NAME
                env_var_name = prefix + field_name.upper()

                if not ctx.mark_seen(env_var_name):
                    continue

                field_line = class_start_line + class_body[: field_match.start()].count("\n")

                yield ctx.create_env_var_node(
                    name=env_var_name,
                    line=field_line,
                    source="pydantic_settings",
                    extra_metadata={
                        "settings_class": class_name,
                        "field_name": field_name,
                        "env_prefix": prefix,
                        "inferred": True,
                    },
                )

                yield ctx.create_reads_edge(
                    target_id=f"env:{env_var_name}",
                    line=field_line,
                    pattern="pydantic_settings",
                )