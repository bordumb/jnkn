# FILE: src/jnkn/parsing/pyspark/extractors/spark_config.py
import re
from typing import Generator, Union

from ....core.types import Edge, Node, NodeType, RelationshipType
from ...base import ExtractionContext


class SparkConfigExtractor:
    """Extract Spark configuration reads."""

    name = "spark_config"
    priority = 80

    # spark.conf.get("key")
    CONF_GET = re.compile(r'spark\.conf\.get\s*\(\s*["\']([^"\']+)["\']')
    CONF_SET = re.compile(r'spark\.conf\.set\s*\(\s*["\']([^"\']+)["\']\s*,')
    SPARK_CONF = re.compile(r'SparkConf\(\)(?:\.set\s*\(\s*["\']([^"\']+)["\'])+', re.DOTALL)

    def can_extract(self, ctx: ExtractionContext) -> bool:
        text_lower = ctx.text.lower()
        return "spark" in text_lower and "conf" in text_lower

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        seen = set()

        # spark.conf.get()
        for match in self.CONF_GET.finditer(ctx.text):
            key = match.group(1)
            if key in seen:
                continue
            seen.add(key)

            line = ctx.get_line_number(match.start())
            config_id = f"config:spark:{key}"

            yield ctx.create_config_node(
                id=config_id,
                name=key,
                line=line,
                config_type="spark",
            )

            yield ctx.create_reads_edge(
                target_id=config_id,
                line=line,
            )