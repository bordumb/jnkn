import re
from typing import Generator, Union

from ....core.types import Edge, Node
from ...base import ExtractionContext


class JavaDefinitionExtractor:
    """Extract Class and Interface definitions from Java code."""

    name = "java_definitions"
    priority = 80

    # public class MyClass extends Parent implements Interface {
    # abstract class MyClass ...
    # interface MyInterface ...
    CLASS_DEF = re.compile(
        r"(?:public|protected|private|abstract|final|static|\s)*"
        r"(class|interface|enum|record)\s+"
        r"(\w+)"
    )

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return "class" in ctx.text or "interface" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        # We only care about top-level definitions usually, but regex finds all
        # To strictly map file -> class, we look for the public class that matches filename

        filename_no_ext = ctx.file_path.stem

        for match in self.CLASS_DEF.finditer(ctx.text):
            def_type = match.group(1)  # class, interface, etc.
            def_name = match.group(2)

            line = ctx.get_line_number(match.start())

            yield ctx.create_code_entity_node(
                name=def_name,
                line=line,
                entity_type=def_type,
                language="java",
                extra_metadata={"is_public": def_name == filename_no_ext},
            )

            entity_id = f"entity:{ctx.file_path}:{def_name}"
            yield ctx.create_contains_edge(target_id=entity_id)
