"""
Standardized Terraform Parser.

Provides parsing for:
- Static .tf files (HCL)
- Terraform Plan JSON (tfplan.json)
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from ...core.types import Edge, Node, NodeType, RelationshipType
from ..base import LanguageParser, ParserContext

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class TerraformResource:
    """Represents a Terraform resource block."""
    type: str
    name: str
    provider: str
    line: int

@dataclass
class TerraformOutput:
    """Represents a Terraform output block."""
    name: str
    description: str | None = None
    line: int = 0

@dataclass
class ResourceChange:
    """Represents a change in a Terraform plan."""
    address: str
    type: str
    name: str
    change_type: str  # create, update, delete
    actions: List[str]


# =============================================================================
# Static Parser (for .tf files)
# =============================================================================

class TerraformParser(LanguageParser):
    """
    Static analysis parser for Terraform (.tf) files.
    """
    
    # Regex for blocks
    OUTPUT_PATTERN = re.compile(r'output\s+"([^"]+)"\s+\{')
    RESOURCE_PATTERN = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"')
    DATA_PATTERN = re.compile(r'data\s+"([^"]+)"\s+"([^"]+)"')
    LOCALS_PATTERN = re.compile(r'locals\s+\{')
    
    # Regex for references (capturing type, name, attr)
    REF_PATTERN = re.compile(r'\b(var|local|data|module)\.([a-zA-Z0-9_\-]+)(?:\.([a-zA-Z0-9_\-]+))?')

    @property
    def name(self) -> str:
        return "terraform"

    @property
    def extensions(self) -> List[str]:
        return [".tf"]

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix == ".tf"

    def parse(self, file_path: Path, content: bytes) -> List[Union[Node, Edge]]:
        results: List[Union[Node, Edge]] = []
        
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            return []
        
        file_id = f"file://{file_path}"
        
        # 1. File Node
        results.append(Node(
            id=file_id,
            name=file_path.name,
            type=NodeType.CODE_FILE,
            path=str(file_path),
            metadata={"language": "hcl"}
        ))

        lines = text.splitlines()
        current_block_id = None
        current_block_type = None 
        block_depth = 0
        
        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith(('#', '//')):
                continue

            # --- Block Detection ---
            
            # Resource
            res_match = self.RESOURCE_PATTERN.search(line)
            if res_match:
                res_type, res_name = res_match.groups()
                # UPDATED: Use dot separator to match Terraform address conventions
                node_id = f"infra:{res_type}.{res_name}"
                current_block_id = node_id
                current_block_type = "resource"
                block_depth = 1
                
                results.append(Node(
                    id=node_id,
                    name=res_name,
                    type=NodeType.INFRA_RESOURCE,
                    metadata={"terraform_type": res_type, "line": line_num}
                ))
                results.append(Edge(source_id=file_id, target_id=node_id, type=RelationshipType.PROVISIONS))
                continue

            # Data
            data_match = self.DATA_PATTERN.search(line)
            if data_match:
                data_type, data_name = data_match.groups()
                node_id = f"infra:data.{data_type}.{data_name}"
                current_block_id = node_id
                current_block_type = "data"
                block_depth = 1
                
                results.append(Node(
                    id=node_id,
                    name=data_name,
                    type=NodeType.INFRA_RESOURCE,
                    metadata={"terraform_type": data_type, "is_data": True, "line": line_num}
                ))
                results.append(Edge(source_id=file_id, target_id=node_id, type=RelationshipType.PROVISIONS))
                continue

            # Output
            out_match = self.OUTPUT_PATTERN.search(line)
            if out_match:
                out_name = out_match.groups()[0]
                node_id = f"infra:output:{out_name}"
                current_block_id = node_id
                current_block_type = "output"
                block_depth = 1
                
                results.append(Node(
                    id=node_id,
                    name=out_name,
                    type=NodeType.CONFIG_KEY,
                    metadata={"line": line_num}
                ))
                results.append(Edge(source_id=file_id, target_id=node_id, type=RelationshipType.PROVISIONS))
                continue

            # Locals
            if self.LOCALS_PATTERN.search(line):
                current_block_id = "locals_block"
                current_block_type = "locals"
                block_depth = 1
                continue

            # --- Block Scope Tracking ---
            
            # Count braces to track depth
            open_braces = line.count('{')
            close_braces = line.count('}')
            block_depth += open_braces - close_braces

            if block_depth <= 0 and current_block_id:
                current_block_id = None
                current_block_type = None
                block_depth = 0
                continue

            # --- Inside Block Analysis ---
            if current_block_id:
                
                # Special handling for 'locals' block definitions
                if current_block_type == "locals":
                    # key = value
                    local_match = re.match(r'([a-zA-Z0-9_\-]+)\s*=', stripped)
                    if local_match:
                        local_name = local_match.group(1)
                        local_id = f"infra:local.{local_name}"
                        
                        # Define the local node
                        results.append(Node(
                            id=local_id,
                            name=local_name,
                            type=NodeType.CONFIG_KEY,
                            metadata={"is_local": True, "line": line_num}
                        ))
                        results.append(Edge(source_id=file_id, target_id=local_id, type=RelationshipType.PROVISIONS))
                        
                        # Extract references from the value part (right side of =)
                        # And link them FROM this local
                        value_part = stripped.split('=', 1)[1]
                        self._extract_references(value_part, local_id, results, line_num)
                        continue

                # General reference extraction for Resources, Data, Outputs
                # If we are in a 'resource' block, references mean dependencies (READS)
                if current_block_type in ("resource", "data", "output"):
                    self._extract_references(stripped, current_block_id, results, line_num)

        return results

    def _extract_references(self, text: str, source_id: str, results: List, line_num: int):
        """Extract var/local/data/module references from text and add edges."""
        for match in self.REF_PATTERN.finditer(text):
            ref_type, ref_name, ref_attr = match.groups()
            
            target_id = None
            
            if ref_type == "var":
                # FUTURE: Link to variable definition
                pass 
                
            elif ref_type == "local":
                target_id = f"infra:local.{ref_name}"
                
            elif ref_type == "data":
                # data.type.name
                if ref_attr:
                    target_id = f"infra:data.{ref_name}.{ref_attr}"
                    
            elif ref_type == "module":
                target_id = f"infra:module.{ref_name}"

            if target_id:
                results.append(Edge(
                    source_id=source_id,
                    target_id=target_id,
                    type=RelationshipType.READS,
                    metadata={"line": line_num}
                ))


# =============================================================================
# Plan Parser (for tfplan.json)
# =============================================================================

class TerraformPlanParser(LanguageParser):
    """
    Parser for Terraform JSON plan output.
    """

    @property
    def name(self) -> str:
        return "terraform_plan"

    @property
    def extensions(self) -> List[str]:
        return [".json"]

    def can_parse(self, file_path: Path) -> bool:
        # Heuristic: Check if filename looks like a plan or content has specific keys
        return file_path.suffix == ".json" and "plan" in file_path.name.lower()

    def parse(self, file_path: Path, content: bytes) -> List[Union[Node, Edge]]:
        results = []
        try:
            plan = json.loads(content)
        except json.JSONDecodeError:
            return []

        if "resource_changes" not in plan:
            return []

        for change in plan["resource_changes"]:
            res_type = change.get("type")
            res_name = change.get("name")
            address = change.get("address")
            
            if not res_type or not res_name:
                continue

            # UPDATED: Use dot separator
            node_id = f"infra:{res_type}.{res_name}"
            
            node = Node(
                id=node_id,
                name=res_name,
                type=NodeType.INFRA_RESOURCE,
                metadata={
                    "terraform_address": address,
                    "change_actions": change.get("change", {}).get("actions", [])
                }
            )
            results.append(node)

        return results


# =============================================================================
# Factory Functions
# =============================================================================

def create_terraform_parser(context: ParserContext | None = None) -> TerraformParser:
    return TerraformParser(context)

def create_terraform_plan_parser(context: ParserContext | None = None) -> TerraformPlanParser:
    return TerraformPlanParser(context)
