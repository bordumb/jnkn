# FILE: src/jnkn/parsing/terraform/extractors/resources.py
import re
from typing import Generator, Union

from ....core.types import Edge, Node, RelationshipType
from ...base import ExtractionContext


class ResourceExtractor:
    """Extract Terraform resource blocks."""

    name = "terraform_resources"
    priority = 100

    # resource "type" "name" { ... }
    RESOURCE_PATTERN = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return "resource" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        for match in self.RESOURCE_PATTERN.finditer(ctx.text):
            res_type, res_name = match.groups()
            line = ctx.get_line_number(match.start())

            node_id = f"infra:{res_type}.{res_name}"

            yield ctx.create_infra_node(
                id=node_id,
                name=res_name,
                line=line,
                infra_type=res_type,
                extra_metadata={"terraform_type": res_type},
            )

            yield Edge(
                source_id=ctx.file_id,
                target_id=node_id,
                type=RelationshipType.PROVISIONS,
            )