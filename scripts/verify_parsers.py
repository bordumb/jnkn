#!/usr/bin/env python3
"""
Junkan Epic 2 - Parser Verification Script

This script directly tests each parser's ability to detect nodes and edges
from test fixtures, bypassing the CLI to verify core parser functionality.

Usage:
    uv run python scripts/verify_parsers.py
    uv run python scripts/verify_parsers.py --debug
"""

import json
import sys
import tempfile
import traceback
from pathlib import Path
from typing import List, Tuple, Any

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

DEBUG = "--debug" in sys.argv


def print_header(text: str) -> None:
    print(f"\n{BLUE}{'═' * 60}{RESET}")
    print(f"{BLUE}{BOLD}{text:^60}{RESET}")
    print(f"{BLUE}{'═' * 60}{RESET}\n")


def print_subheader(text: str) -> None:
    print(f"\n{CYAN}{'─' * 50}{RESET}")
    print(f"{CYAN}{text}{RESET}")
    print(f"{CYAN}{'─' * 50}{RESET}")


def success(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def failure(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warning(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}•{RESET} {msg}")


def create_parser_instance(parser_class, context=None):
    """Try different ways to instantiate a parser, with detailed error logging."""
    errors = []
    
    # Try with no args first
    try:
        return parser_class()
    except TypeError as e:
        errors.append(f"No args: {e}")
    except Exception as e:
        errors.append(f"No args (other): {e}")
    
    # Try with context keyword arg
    try:
        return parser_class(context=context)
    except TypeError as e:
        errors.append(f"context=context: {e}")
    except Exception as e:
        errors.append(f"context=context (other): {e}")
    
    # Try with context positional arg
    try:
        return parser_class(context)
    except TypeError as e:
        errors.append(f"Positional context: {e}")
    except Exception as e:
        errors.append(f"Positional context (other): {e}")
    
    # Try with None
    try:
        return parser_class(None)
    except TypeError as e:
        errors.append(f"None: {e}")
    except Exception as e:
        errors.append(f"None (other): {e}")
    
    if DEBUG:
        print(f"    {RED}Instantiation attempts failed:{RESET}")
        for err in errors:
            print(f"      - {err}")
    
    raise TypeError(f"Could not instantiate {parser_class.__name__}: {errors[0] if errors else 'unknown'}")


# =============================================================================
# Test Fixtures
# =============================================================================

PYTHON_CONFIG = '''
"""Application configuration with multiple env var patterns."""
import os
from os import getenv, environ

DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
REDIS_URL = os.environ.get("REDIS_URL")
API_KEY = os.environ["API_KEY"]
SECRET_KEY = getenv("SECRET_KEY")
DEBUG_MODE = environ.get("DEBUG_MODE", "false")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")

class Config:
    db_host = os.getenv("DB_HOST")
    db_name = os.environ.get("DB_NAME", "myapp")
'''

TERRAFORM_MAIN = '''
terraform {
  required_version = ">= 1.0"
}

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
}

resource "aws_db_instance" "payment_db_host" {
  identifier = "payment-db"
  engine     = "postgres"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

output "vpc_id" {
  value = aws_vpc.main.id
}
'''

DBT_MANIFEST = {
    "metadata": {"dbt_schema_version": "v10", "dbt_version": "1.6.0"},
    "nodes": {
        "model.analytics.stg_customers": {
            "resource_type": "model",
            "name": "stg_customers",
            "schema": "staging",
            "depends_on": {"nodes": ["source.analytics.raw.customers"]},
        },
        "model.analytics.fct_orders": {
            "resource_type": "model",
            "name": "fct_orders",
            "schema": "marts",
            "depends_on": {"nodes": ["model.analytics.stg_customers"]},
        },
    },
    "sources": {
        "source.analytics.raw.customers": {
            "resource_type": "source",
            "name": "customers",
            "source_name": "raw",
            "schema": "raw_data",
        },
    },
    "exposures": {},
}

KUBERNETES_YAML = '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: production
spec:
  template:
    spec:
      containers:
      - name: payment-service
        image: payment-service:v1.0
        env:
        - name: DATABASE_HOST
          value: "postgres.production.svc"
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: api_key
'''

JAVASCRIPT_CONFIG = '''
const databaseHost = process.env.DATABASE_HOST;
const apiKey = process.env["API_KEY"];
const { REDIS_URL } = process.env;
const publicApiUrl = process.env.NEXT_PUBLIC_API_URL;
'''


# =============================================================================
# Test Functions
# =============================================================================

def test_python_parser() -> Tuple[bool, List[str], List[str]]:
    """Test the Python parser."""
    detected = []
    errors = []
    
    try:
        from junkan.parsing.python.parser import PythonParser
        from junkan.parsing.base import ParserContext
        
        context = ParserContext(root_dir=Path.cwd())
        parser = create_parser_instance(PythonParser, context)
        
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(PYTHON_CONFIG.encode())
            temp_path = Path(f.name)
        
        try:
            results = list(parser.parse(temp_path, PYTHON_CONFIG.encode()))
            
            for node in results:
                node_type = str(getattr(node, 'type', ''))
                if 'env' in node_type.lower():
                    detected.append(f"ENV: {getattr(node, 'name', str(node))}")
                elif hasattr(node, 'name'):
                    detected.append(f"NODE: {node.name}")
        finally:
            temp_path.unlink()
            
    except ImportError as e:
        errors.append(f"Import error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return len(detected) > 0, detected, errors


def test_terraform_parser() -> Tuple[bool, List[str], List[str]]:
    """Test the Terraform parser."""
    detected = []
    errors = []
    
    try:
        from junkan.parsing.terraform.parser import TerraformParser
        from junkan.parsing.base import ParserContext
        
        context = ParserContext(root_dir=Path.cwd())
        parser = create_parser_instance(TerraformParser, context)
        
        with tempfile.NamedTemporaryFile(suffix=".tf", delete=False) as f:
            f.write(TERRAFORM_MAIN.encode())
            temp_path = Path(f.name)
        
        try:
            results = list(parser.parse(temp_path, TERRAFORM_MAIN.encode()))
            
            for item in results:
                if hasattr(item, 'name'):
                    detected.append(f"RESOURCE: {item.name}")
                elif hasattr(item, 'source_id'):
                    detected.append(f"EDGE: {item.source_id} -> {item.target_id}")
        finally:
            temp_path.unlink()
            
    except ImportError as e:
        errors.append(f"Import error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return len(detected) > 0, detected, errors


def test_dbt_parser() -> Tuple[bool, List[str], List[str]]:
    """Test the dbt manifest parser."""
    detected = []
    errors = []
    
    try:
        from junkan.parsing.dbt.manifest_parser import DbtManifestParser
        from junkan.parsing.base import ParserContext
        
        context = ParserContext(root_dir=Path.cwd())
        parser = create_parser_instance(DbtManifestParser, context)
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(json.dumps(DBT_MANIFEST).encode())
            temp_path = Path(f.name)
        
        try:
            results = list(parser.parse(temp_path, json.dumps(DBT_MANIFEST).encode()))
            
            for item in results:
                if hasattr(item, 'name'):
                    detected.append(f"MODEL: {item.name} ({getattr(item, 'type', 'unknown')})")
                elif hasattr(item, 'source_id'):
                    detected.append(f"LINEAGE: {item.source_id} -> {item.target_id}")
        finally:
            temp_path.unlink()
            
    except ImportError as e:
        errors.append(f"Import error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return len(detected) > 0, detected, errors


def test_kubernetes_parser() -> Tuple[bool, List[str], List[str]]:
    """Test the Kubernetes parser."""
    detected = []
    errors = []
    
    try:
        from junkan.parsing.kubernetes.parser import KubernetesParser
        from junkan.parsing.base import ParserContext
        
        context = ParserContext(root_dir=Path.cwd())
        parser = create_parser_instance(KubernetesParser, context)
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(KUBERNETES_YAML.encode())
            temp_path = Path(f.name)
        
        try:
            results = list(parser.parse(temp_path, KUBERNETES_YAML.encode()))
            
            for item in results:
                node_type = str(getattr(item, 'type', ''))
                if 'env' in node_type.lower():
                    detected.append(f"K8S_ENV: {getattr(item, 'name', str(item))}")
                elif hasattr(item, 'name'):
                    detected.append(f"K8S_RESOURCE: {item.name}")
                elif hasattr(item, 'source_id'):
                    detected.append(f"K8S_REF: {item.source_id} -> {item.target_id}")
        finally:
            temp_path.unlink()
            
    except ImportError as e:
        errors.append(f"Import error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return len(detected) > 0, detected, errors


def test_javascript_parser() -> Tuple[bool, List[str], List[str]]:
    """Test the JavaScript parser."""
    detected = []
    errors = []
    
    try:
        from junkan.parsing.javascript.parser import JavaScriptParser
        from junkan.parsing.base import ParserContext
        
        context = ParserContext(root_dir=Path.cwd())
        parser = create_parser_instance(JavaScriptParser, context)
        
        with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as f:
            f.write(JAVASCRIPT_CONFIG.encode())
            temp_path = Path(f.name)
        
        try:
            results = list(parser.parse(temp_path, JAVASCRIPT_CONFIG.encode()))
            
            for item in results:
                node_type = str(getattr(item, 'type', ''))
                if 'env' in node_type.lower():
                    detected.append(f"JS_ENV: {getattr(item, 'name', str(item))}")
                elif hasattr(item, 'name'):
                    detected.append(f"JS_NODE: {item.name}")
        finally:
            temp_path.unlink()
            
    except ImportError as e:
        errors.append(f"Import error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return len(detected) > 0, detected, errors


def test_stitching() -> Tuple[bool, List[str], List[str]]:
    """Test the stitching engine."""
    detected = []
    errors = []
    
    try:
        from junkan.core.graph import DependencyGraph
        from junkan.core.types import Node, NodeType
        from junkan.core.stitching import Stitcher
        
        graph = DependencyGraph()
        
        graph.add_node(Node(
            id="env:PAYMENT_DB_HOST",
            name="PAYMENT_DB_HOST",
            type=NodeType.ENV_VAR,
            tokens=("payment", "db", "host"),
        ))
        
        graph.add_node(Node(
            id="infra:aws_db_instance.payment_db_host",
            name="payment_db_host",
            type=NodeType.INFRA_RESOURCE,
            tokens=("payment", "db", "host"),
        ))
        
        stitcher = Stitcher()
        edges = stitcher.stitch(graph)
        
        for edge in edges:
            detected.append(
                f"STITCH: {edge.source_id} -> {edge.target_id} "
                f"(confidence: {edge.confidence:.2f})"
            )
        
        stats = stitcher.get_stats()
        detected.append(f"Total edges created: {stats.get('total_edges_created', 0)}")
        
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return len(detected) > 0 and any("STITCH" in d for d in detected), detected, errors


def test_blast_radius() -> Tuple[bool, List[str], List[str]]:
    """Test the blast radius analyzer."""
    detected = []
    errors = []
    result = {}
    
    try:
        from junkan.core.graph import DependencyGraph
        from junkan.core.types import Node, Edge, NodeType, RelationshipType
        from junkan.analysis.blast_radius import BlastRadiusAnalyzer
        
        graph = DependencyGraph()
        
        graph.add_node(Node(id="env:DB_HOST", name="DB_HOST", type=NodeType.ENV_VAR))
        graph.add_node(Node(id="file:config.py", name="config.py", type=NodeType.CODE_FILE))
        graph.add_node(Node(id="file:app.py", name="app.py", type=NodeType.CODE_FILE))
        graph.add_node(Node(id="file:main.py", name="main.py", type=NodeType.CODE_FILE))
        
        graph.add_edge(Edge(source_id="env:DB_HOST", target_id="file:config.py", type=RelationshipType.PROVIDES))
        graph.add_edge(Edge(source_id="file:config.py", target_id="file:app.py", type=RelationshipType.IMPORTS))
        graph.add_edge(Edge(source_id="file:app.py", target_id="file:main.py", type=RelationshipType.IMPORTS))
        
        analyzer = BlastRadiusAnalyzer(graph=graph)
        result = analyzer.calculate(["env:DB_HOST"])
        
        detected.append(f"Impacted count: {result.get('total_impacted_count', 0)}")
        for artifact in result.get('impacted_artifacts', []):
            detected.append(f"IMPACTED: {artifact}")
        
    except Exception as e:
        errors.append(f"Error: {e}")
        if DEBUG:
            traceback.print_exc()
    
    return result.get('total_impacted_count', 0) == 3, detected, errors


# =============================================================================
# Main
# =============================================================================

def main():
    print_header("JUNKAN EPIC 2 - PARSER VERIFICATION")
    
    if DEBUG:
        info("Debug mode enabled - will show full tracebacks")
    
    results = {}
    
    tests = [
        ("Python Parser", test_python_parser),
        ("Terraform Parser", test_terraform_parser),
        ("dbt Manifest Parser", test_dbt_parser),
        ("Kubernetes Parser", test_kubernetes_parser),
        ("JavaScript Parser", test_javascript_parser),
        ("Stitching Engine", test_stitching),
        ("Blast Radius Analyzer", test_blast_radius),
    ]
    
    for name, test_func in tests:
        print_subheader(f"Testing: {name}")
        
        passed, detected, errors = test_func()
        results[name] = passed
        
        if errors:
            for err in errors:
                failure(err)
        
        if detected:
            for item in detected[:10]:
                info(item)
            if len(detected) > 10:
                info(f"... and {len(detected) - 10} more")
        
        if passed:
            success(f"{name} working!")
        else:
            failure(f"{name} not working or not fully implemented")
    
    print_header("SUMMARY")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name}")
    
    print()
    
    if passed_count == total_count:
        print(f"{GREEN}{BOLD}✅ ALL TESTS PASSED ({passed_count}/{total_count}){RESET}")
        return 0
    elif passed_count > 0:
        print(f"{YELLOW}{BOLD}⚠️  PARTIAL SUCCESS ({passed_count}/{total_count} passed){RESET}")
        return 1
    else:
        print(f"{RED}{BOLD}❌ ALL TESTS FAILED{RESET}")
        return 2


if __name__ == "__main__":
    sys.exit(main())