import re
from typing import Generator, Union

from ....core.types import Edge, Node, NodeType, RelationshipType
from ...base import ExtractionContext


class SQLFileExtractor:
    """Extract ref() and source() calls from dbt SQL files."""

    name = "dbt_sql"
    priority = 90

    # Jinja ref/source patterns
    # {{ ref('model') }} or {{ ref("model") }}
    REF_PATTERN = re.compile(r"\{\{\s*ref\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}")

    # {{ source('src', 'table') }}
    SOURCE_PATTERN = re.compile(
        r"\{\{\s*source\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}"
    )

    # {{ config(...) }}
    CONFIG_PATTERN = re.compile(r"\{\{\s*config\s*\(([^)]+)\)\s*\}\}")

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return ctx.file_path.suffix == ".sql" and "{{" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        # Infer model name from file path
        model_name = ctx.file_path.stem
        model_id = f"data:model:{model_name}"

        # Simplistic config parse to check tags/materialization
        # A full Jinja parser would be better, but regex suffices for simple metadata
        config_meta = {}
        if cm := self.CONFIG_PATTERN.search(ctx.text):
            config_str = cm.group(1)
            if "materialized" in config_str:
                config_meta["materialized"] = "derived"  # placeholder

        yield Node(
            id=model_id,
            name=model_name,
            type=NodeType.DATA_ASSET,
            path=str(ctx.file_path),
            metadata={"resource_type": "model", "from_sql": True, **config_meta},
        )

        yield Edge(
            source_id=ctx.file_id,
            target_id=model_id,
            type=RelationshipType.CONTAINS,
        )

        # Extract ref() dependencies
        for match in self.REF_PATTERN.finditer(ctx.text):
            ref_name = match.group(1)
            ref_id = f"data:model:{ref_name}"
            line = ctx.text[: match.start()].count("\n") + 1

            yield Edge(
                source_id=model_id,
                target_id=ref_id,
                type=RelationshipType.DEPENDS_ON,
                metadata={"line": line, "type": "ref"},
            )

        # Extract source() dependencies
        for match in self.SOURCE_PATTERN.finditer(ctx.text):
            source_name, table_name = match.groups()
            source_id = f"data:source:{source_name}.{table_name}"
            line = ctx.text[: match.start()].count("\n") + 1

            yield Edge(
                source_id=model_id,
                target_id=source_id,
                type=RelationshipType.READS,
                metadata={"line": line, "type": "source"},
            )
