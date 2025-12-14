import re
from typing import Generator, Union

from ....core.types import Edge, Node
from ...base import ExtractionContext


class GoDefinitionExtractor:
    """
    Extract function and type definitions from Go code.

    Handles:
    - Functions: func MyFunc(...)
    - Methods: func (r *Receiver) Method(...)
    - Types: type MyStruct struct { ... }
    - Interfaces: type MyInterface interface { ... }
    """

    name = "go_definitions"
    priority = 80

    # func FunctionName(...)
    FUNC_DEF = re.compile(r"^func\s+(\w+)\s*\(", re.MULTILINE)

    # func (recv) MethodName(...)
    METHOD_DEF = re.compile(r"^func\s+\([^)]+\)\s+(\w+)\s*\(", re.MULTILINE)

    # type TypeName struct/interface
    TYPE_DEF = re.compile(r"^type\s+(\w+)\s+(struct|interface)", re.MULTILINE)

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return "func" in ctx.text or "type" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        filename_no_ext = ctx.file_path.stem

        # 1. Functions
        for match in self.FUNC_DEF.finditer(ctx.text):
            func_name = match.group(1)
            line = ctx.get_line_number(match.start())

            is_exported = func_name[0].isupper()

            yield ctx.create_code_entity_node(
                name=func_name,
                line=line,
                entity_type="function",
                language="go",
                extra_metadata={"is_exported": is_exported},
            )

            # Link file to function
            entity_id = f"entity:{ctx.file_path}:{func_name}"
            yield ctx.create_contains_edge(target_id=entity_id)

        # 2. Methods
        for match in self.METHOD_DEF.finditer(ctx.text):
            method_name = match.group(1)
            line = ctx.get_line_number(match.start())

            is_exported = method_name[0].isupper()

            yield ctx.create_code_entity_node(
                name=method_name,
                line=line,
                entity_type="method",
                language="go",
                extra_metadata={"is_exported": is_exported},
            )

            entity_id = f"entity:{ctx.file_path}:{method_name}"
            yield ctx.create_contains_edge(target_id=entity_id)

        # 3. Types (Structs/Interfaces)
        for match in self.TYPE_DEF.finditer(ctx.text):
            type_name = match.group(1)
            kind = match.group(2)  # struct or interface
            line = ctx.get_line_number(match.start())

            is_exported = type_name[0].isupper()

            yield ctx.create_code_entity_node(
                name=type_name,
                line=line,
                entity_type=kind,
                language="go",
                extra_metadata={"is_exported": is_exported},
            )

            entity_id = f"entity:{ctx.file_path}:{type_name}"
            yield ctx.create_contains_edge(target_id=entity_id)
