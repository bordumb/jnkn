import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import ExtractionContext


class DeltaLakeExtractor:
    """Extract Delta Lake specific operations."""

    name = "delta_lake"
    priority = 70

    # DeltaTable.forPath(spark, "path")
    DELTA_FOR_PATH = re.compile(r'DeltaTable\.forPath\s*\([^,]+,\s*["\']([^"\']+)["\']')
    # DeltaTable.forName(spark, "name")
    DELTA_FOR_NAME = re.compile(r'DeltaTable\.forName\s*\([^,]+,\s*["\']([^"\']+)["\']')
    # .mergeInto() target
    MERGE_INTO = re.compile(r'\.merge\s*\([^,]+,\s*["\']([^"\']+)["\']\s*\)')

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return "delta" in ctx.text.lower() or "DeltaTable" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        for pattern, op in [
            (self.DELTA_FOR_PATH, "read"),
            (self.DELTA_FOR_NAME, "read"),
        ]:
            for match in pattern.finditer(ctx.text):
                table_ref = match.group(1)
                table_id = f"data:delta:{table_ref}"
                line = ctx.get_line_number(match.start())

                yield ctx.create_data_asset_node(
                    id=table_id,
                    name=table_ref,
                    line=line,
                    asset_type="delta",
                    extra_metadata={"format": "delta"},
                )

                rel_type = RelationshipType.READS if op == "read" else RelationshipType.WRITES
                yield Edge(
                    source_id=ctx.file_id,
                    target_id=table_id,
                    type=rel_type,
                )
