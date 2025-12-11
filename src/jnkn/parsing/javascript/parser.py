"""
JavaScript/TypeScript Parser for jnkn.

This parser provides comprehensive extraction from JS/TS files.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Set, Union

from ...core.types import Edge, Node, NodeType, RelationshipType
from ..base import (
    LanguageParser,
    ParserCapability,
    ParserContext,
)

logger = logging.getLogger(__name__)

# Check if tree-sitter is available
try:
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.debug("tree-sitter not available, using regex fallback")


# Tree-sitter query for JavaScript/TypeScript environment variables
ENV_VAR_QUERY = """
(member_expression
  object: (member_expression
    object: (identifier) @_process
    property: (property_identifier) @_env)
  property: (property_identifier) @env_var
  (#eq? @_process "process")
  (#eq? @_env "env"))

(subscript_expression
  object: (member_expression
    object: (identifier) @_process
    property: (property_identifier) @_env)
  index: (string) @env_var_bracket
  (#eq? @_process "process")
  (#eq? @_env "env"))

(variable_declarator
  name: (object_pattern
    (shorthand_property_identifier_pattern) @destructured_var)
  value: (member_expression
    object: (identifier) @_process
    property: (property_identifier) @_env)
  (#eq? @_process "process")
  (#eq? @_env "env"))

(member_expression
  object: (member_expression
    object: (member_expression
      object: (identifier) @_import
      property: (property_identifier) @_meta)
    property: (property_identifier) @_env)
  property: (property_identifier) @vite_env_var
  (#eq? @_import "import")
  (#eq? @_meta "meta")
  (#eq? @_env "env"))
"""

# Import query
IMPORT_QUERY = """
(import_statement
  source: (string) @import_source)

(call_expression
  function: (import)
  arguments: (arguments (string) @dynamic_import))

(call_expression
  function: (identifier) @_require
  arguments: (arguments (string) @require_source)
  (#eq? @_require "require"))

(export_statement
  source: (string) @export_source)
"""

# Definitions query
DEFINITIONS_QUERY = """
(function_declaration
  name: (identifier) @function_def)

(class_declaration
  name: (identifier) @class_def)
"""


@dataclass
class JSEnvVar:
    name: str
    pattern: str
    line: int
    column: int
    is_public: bool = False
    framework: str | None = None

    def to_node_id(self) -> str:
        return f"env:{self.name}"


@dataclass
class JSImport:
    source: str
    is_dynamic: bool
    is_commonjs: bool
    line: int

    def to_file_path(self) -> str:
        source = self.source.strip("'\"")
        if source.startswith("."):
            return source
        return f"node_modules/{source}"


class JavaScriptParser(LanguageParser):
    
    # Regex patterns for fallback parsing
    ENV_VAR_PATTERNS = [
        (r'process\.env\.([A-Z][A-Z0-9_]*)', "process.env."),
        (r'process\.env\[["\']([^"\']+)["\']\]', "process.env[]"),
        (r'const\s*\{\s*([A-Z][A-Z0-9_]*(?:\s*,\s*[A-Z][A-Z0-9_]*)*)\s*\}\s*=\s*process\.env', "destructuring"),
        (r'import\.meta\.env\.([A-Z][A-Z0-9_]*)', "import.meta.env"),
    ]

    IMPORT_PATTERNS = [
        # import x from "module"
        re.compile(r'import\s+.*\s+from\s+["\']([^"\']+)["\']', re.MULTILINE),
        # import "module"
        re.compile(r'import\s+["\']([^"\']+)["\']', re.MULTILINE),
        # require("module")
        re.compile(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)', re.MULTILINE),
        # await import("module") - Dynamic Import
        re.compile(r'import\s*\(\s*["\']([^"\']+)["\']\s*\)', re.MULTILINE),
        # export * from "module"
        re.compile(r'export\s+.*\s+from\s+["\']([^"\']+)["\']', re.MULTILINE),
    ]

    DEF_PATTERN = re.compile(
        r'^(?:export\s+)?(?:async\s+)?(?:function|class)\s+(\w+)',
        re.MULTILINE
    )

    def __init__(self, context: ParserContext | None = None):
        super().__init__(context)
        self._tree_sitter_initialized = False
        self._ts_parser = None
        self._ts_language = None

    @property
    def name(self) -> str:
        return "javascript"

    @property
    def extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    @property
    def description(self) -> str:
        return "JavaScript/TypeScript parser with comprehensive env var detection"

    def get_capabilities(self) -> List[ParserCapability]:
        return [
            ParserCapability.IMPORTS,
            ParserCapability.ENV_VARS,
            ParserCapability.DEFINITIONS,
        ]

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.extensions

    def _init_tree_sitter(self, file_path: Path) -> bool:
        if not TREE_SITTER_AVAILABLE:
            return False

        ext = file_path.suffix.lower()
        if ext in (".ts", ".tsx"):
            lang_name = "typescript"
        else:
            lang_name = "javascript"

        try:
            self._ts_parser = get_parser(lang_name)
            self._ts_language = get_language(lang_name)
            return True
        except Exception as e:
            self._logger.warning(f"Failed to initialize tree-sitter for {lang_name}: {e}")
            return False

    def parse(
        self,
        file_path: Path,
        content: bytes,
    ) -> Generator[Union[Node, Edge], None, None]:
        from ...core.types import ScanMetadata

        ext = file_path.suffix.lower()
        if ext in (".ts", ".tsx"):
            language = "typescript"
        else:
            language = "javascript"

        try:
            file_hash = ScanMetadata.compute_hash(str(file_path))
        except Exception:
            file_hash = ""

        file_id = f"file://{file_path}"
        yield Node(
            id=file_id,
            name=file_path.name,
            type=NodeType.CODE_FILE,
            path=str(file_path),
            language=language,
            file_hash=file_hash,
        )

        try:
            text = content.decode(self.context.encoding)
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as e:
                self._logger.error(f"Failed to decode {file_path}: {e}")
                return

        if self._init_tree_sitter(file_path):
            yield from self._parse_with_tree_sitter(file_path, file_id, content, text)
        else:
            yield from self._parse_with_regex(file_path, file_id, text)

    def _parse_with_tree_sitter(
        self,
        file_path: Path,
        file_id: str,
        content: bytes,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        tree = self._ts_parser.parse(content)
        yield from self._extract_env_vars_ts(file_path, file_id, tree, text)
        yield from self._extract_imports_ts(file_path, file_id, tree, text)
        yield from self._extract_definitions_ts(file_path, file_id, tree, text)

    def _extract_env_vars_ts(
        self,
        file_path: Path,
        file_id: str,
        tree,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        try:
            query = self._ts_language.query(ENV_VAR_QUERY)
            captures = query.captures(tree.root_node)
        except Exception as e:
            self._logger.debug(f"Tree-sitter env query failed: {e}")
            yield from self._extract_env_vars_regex(file_path, file_id, text)
            return

        seen_vars: Set[str] = set()

        for node, capture_name in captures:
            if capture_name not in ("env_var", "env_var_bracket", "destructured_var", "vite_env_var"):
                continue

            var_name = node.text.decode("utf-8").strip('"\'')

            if var_name in seen_vars:
                continue
            seen_vars.add(var_name)

            framework = self._detect_framework(var_name)
            is_public = var_name.startswith(("NEXT_PUBLIC_", "VITE_", "REACT_APP_"))

            env_id = f"env:{var_name}"

            yield Node(
                id=env_id,
                name=var_name,
                type=NodeType.ENV_VAR,
                metadata={
                    "source": capture_name,
                    "file": str(file_path),
                    "line": node.start_point[0] + 1,
                    "framework": framework,
                    "is_public": is_public,
                },
            )

            yield Edge(
                source_id=file_id,
                target_id=env_id,
                type=RelationshipType.READS,
                metadata={"pattern": capture_name},
            )

    def _extract_imports_ts(
        self,
        file_path: Path,
        file_id: str,
        tree,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        try:
            query = self._ts_language.query(IMPORT_QUERY)
            captures = query.captures(tree.root_node)
        except Exception as e:
            self._logger.debug(f"Tree-sitter import query failed: {e}")
            yield from self._extract_imports_regex(file_path, file_id, text)
            return

        seen_imports: Set[str] = set()

        for node, capture_name in captures:
            if capture_name not in ("import_source", "dynamic_import", "require_source", "export_source"):
                continue

            module_name = node.text.decode("utf-8").strip('"\'')

            if module_name in seen_imports:
                continue
            seen_imports.add(module_name)

            is_commonjs = capture_name == "require_source"
            is_dynamic = capture_name == "dynamic_import"

            if module_name.startswith("."):
                target_path = module_name
            else:
                target_path = f"node_modules/{module_name}"

            target_id = f"file://{target_path}"

            yield Node(
                id=target_id,
                name=module_name,
                type=NodeType.UNKNOWN,
                metadata={
                    "virtual": True,
                    "import_name": module_name,
                    "is_commonjs": is_commonjs,
                    "is_dynamic": is_dynamic,
                },
            )

            yield Edge(
                source_id=file_id,
                target_id=target_id,
                type=RelationshipType.IMPORTS,
                metadata={
                    "line": node.start_point[0] + 1,
                    "is_commonjs": is_commonjs,
                    "is_dynamic": is_dynamic,
                },
            )

    def _extract_definitions_ts(
        self,
        file_path: Path,
        file_id: str,
        tree,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        try:
            query = self._ts_language.query(DEFINITIONS_QUERY)
            captures = query.captures(tree.root_node)
        except Exception:
            yield from self._extract_definitions_regex(file_path, file_id, text)
            return

        seen_defs: Set[str] = set()

        for node, capture_name in captures:
            def_name = node.text.decode("utf-8")

            if def_name in seen_defs:
                continue
            seen_defs.add(def_name)

            entity_type = "function" if "function" in capture_name else "class"
            entity_id = f"entity:{file_path}:{def_name}"

            yield Node(
                id=entity_id,
                name=def_name,
                type=NodeType.CODE_ENTITY,
                path=str(file_path),
                language="javascript",
                metadata={
                    "entity_type": entity_type,
                    "line": node.start_point[0] + 1,
                },
            )

            yield Edge(
                source_id=file_id,
                target_id=entity_id,
                type=RelationshipType.CONTAINS,
            )

    def _parse_with_regex(
        self,
        file_path: Path,
        file_id: str,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        yield from self._extract_env_vars_regex(file_path, file_id, text)
        yield from self._extract_imports_regex(file_path, file_id, text)
        yield from self._extract_definitions_regex(file_path, file_id, text)

    def _extract_env_vars_regex(
        self,
        file_path: Path,
        file_id: str,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        seen_vars: Set[str] = set()

        for pattern, pattern_name in self.ENV_VAR_PATTERNS:
            regex = re.compile(pattern)

            for match in regex.finditer(text):
                var_names = match.group(1)

                if "," in var_names:
                    names = [n.strip() for n in var_names.split(",")]
                else:
                    names = [var_names]

                for var_name in names:
                    if var_name in seen_vars:
                        continue
                    seen_vars.add(var_name)

                    line = text[:match.start()].count('\n') + 1
                    framework = self._detect_framework(var_name)
                    is_public = var_name.startswith(("NEXT_PUBLIC_", "VITE_", "REACT_APP_"))

                    env_id = f"env:{var_name}"

                    yield Node(
                        id=env_id,
                        name=var_name,
                        type=NodeType.ENV_VAR,
                        metadata={
                            "source": pattern_name,
                            "file": str(file_path),
                            "line": line,
                            "framework": framework,
                            "is_public": is_public,
                        },
                    )

                    yield Edge(
                        source_id=file_id,
                        target_id=env_id,
                        type=RelationshipType.READS,
                        metadata={"pattern": pattern_name},
                    )

    def _extract_imports_regex(
        self,
        file_path: Path,
        file_id: str,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        seen_imports: Set[str] = set()

        for pattern in self.IMPORT_PATTERNS:
            for match in pattern.finditer(text):
                module_name = match.group(1)

                if module_name in seen_imports:
                    continue
                seen_imports.add(module_name)

                # Determine import type
                matched_text = match.group(0)
                is_commonjs = "require" in matched_text
                # If regex has 'import(' then it is dynamic
                is_dynamic = "import(" in matched_text or ("import" in matched_text and "(" in matched_text)

                if module_name.startswith("."):
                    target_path = module_name
                else:
                    target_path = f"node_modules/{module_name}"

                target_id = f"file://{target_path}"

                yield Node(
                    id=target_id,
                    name=module_name,
                    type=NodeType.UNKNOWN,
                    metadata={
                        "virtual": True,
                        "import_name": module_name,
                        "is_commonjs": is_commonjs,
                        "is_dynamic": is_dynamic,
                    },
                )

                yield Edge(
                    source_id=file_id,
                    target_id=target_id,
                    type=RelationshipType.IMPORTS,
                    metadata={"is_commonjs": is_commonjs, "is_dynamic": is_dynamic},
                )

    def _extract_definitions_regex(
        self,
        file_path: Path,
        file_id: str,
        text: str,
    ) -> Generator[Union[Node, Edge], None, None]:
        seen_defs: Set[str] = set()

        for match in self.DEF_PATTERN.finditer(text):
            def_name = match.group(1)

            if def_name in seen_defs:
                continue
            seen_defs.add(def_name)

            entity_id = f"entity:{file_path}:{def_name}"

            yield Node(
                id=entity_id,
                name=def_name,
                type=NodeType.CODE_ENTITY,
                path=str(file_path),
                language="javascript",
                metadata={"entity_type": "function_or_class"},
            )

            yield Edge(
                source_id=file_id,
                target_id=entity_id,
                type=RelationshipType.CONTAINS,
            )

    @staticmethod
    def _detect_framework(var_name: str) -> str | None:
        if var_name.startswith("NEXT_PUBLIC_") or var_name.startswith("NEXT_"):
            return "nextjs"
        elif var_name.startswith("VITE_"):
            return "vite"
        elif var_name.startswith("REACT_APP_"):
            return "create-react-app"
        elif var_name.startswith("NUXT_"):
            return "nuxt"
        elif var_name.startswith("GATSBY_"):
            return "gatsby"
        return None


def create_javascript_parser(context: ParserContext | None = None) -> JavaScriptParser:
    return JavaScriptParser(context)
