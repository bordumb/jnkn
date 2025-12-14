"""
Import Extractor for JavaScript/TypeScript.
"""

import re
from typing import Generator, Union

from ....core.types import Edge, Node, NodeType, RelationshipType
from ...base import ExtractionContext


class ImportExtractor:
    """
    Extract import/require statements.

    Handles:
    - ES Modules: import x from 'y'
    - CommonJS: require('y')
    - Dynamic: import('y')
    """

    name = "js_imports"
    priority = 90

    PATTERNS = [
        # import ... from "module"
        (re.compile(r'import\s+.*\s+from\s+["\']([^"\']+)["\']'), "esm"),
        # import "module" (side-effects)
        (re.compile(r'import\s+["\']([^"\']+)["\']'), "esm"),
        # require("module")
        (re.compile(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'), "commonjs"),
        # await import("module")
        (re.compile(r'import\s*\(\s*["\']([^"\']+)["\']\s*\)'), "dynamic"),
        # export ... from "module"
        (re.compile(r'export\s+.*\s+from\s+["\']([^"\']+)["\']'), "esm"),
    ]

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return "import" in ctx.text or "require" in ctx.text or "export" in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        seen_imports = set()

        for regex, kind in self.PATTERNS:
            for match in regex.finditer(ctx.text):
                module_name = match.group(1)

                if module_name in seen_imports:
                    continue
                seen_imports.add(module_name)

                line = ctx.get_line_number(match.start())

                # Resolve path
                if module_name.startswith("."):
                    # Relative import
                    target_path = module_name
                else:
                    # Package import
                    target_path = f"node_modules/{module_name}"

                target_id = f"file://{target_path}"

                # NOTE: We do NOT use ctx.create_node here because the target node
                # represents an external file/package, so its 'path' should NOT be the current file.
                yield Node(
                    id=target_id,
                    name=module_name,
                    type=NodeType.CODE_FILE,  # Virtual file or package
                    path=target_path,  # Path points to the target
                    metadata={"virtual": True, "import_type": kind, "line": line},
                )

                yield ctx.create_reads_edge(
                    target_id=target_id,
                    line=line,
                    pattern=kind,
                )
                # Also yield classic imports edge
                yield Edge(
                    source_id=ctx.file_id,
                    target_id=target_id,
                    type=RelationshipType.IMPORTS,
                    metadata={"kind": kind, "line": line},
                )
