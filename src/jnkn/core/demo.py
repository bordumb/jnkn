"""
Demo Manager - Scaffolds a perfect example project.

This module provides the logic to generate a demo repository structure
that showcases Jnkan's cross-domain stitching capabilities. It creates
files with intentional dependencies between Python, Terraform, and Kubernetes,
initializes a git repo, and commits a breaking change to a feature branch.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class DemoManager:
    """
    Manages the creation of the demo environment.
    """

    # Python code that uses env vars
    APP_PY = """
import os
import logging

# CRITICAL: This connects to the database provisioned in Terraform
DB_HOST = os.getenv("PAYMENT_DB_HOST")
DB_PORT = os.getenv("PAYMENT_DB_PORT", "5432")
DB_USER = os.getenv("PAYMENT_DB_USER", "admin")
DB_PASS = os.getenv("PAYMENT_DB_PASSWORD") # Secret

# Redis Cache Connection
CACHE_HOST = os.getenv("REDIS_PRIMARY_ENDPOINT")
CACHE_PORT = os.getenv("REDIS_PORT", "6379")

# Feature Flags
ENABLE_NEW_UI = os.getenv("FEATURE_NEW_UI", "false")
MAX_RETRIES = os.getenv("APP_MAX_RETRIES", "3")

# S3 Bucket for reports
REPORT_BUCKET = os.getenv("REPORT_BUCKET_NAME")

def connect():
    if not DB_HOST:
        raise ValueError("Database host not configured!")
    print(f"Connecting to {DB_HOST}:{DB_PORT}...")
    print(f"Cache: {CACHE_HOST}")
"""

    # V1: Safe Infrastructure (Matches APP_PY)
    INFRA_TF_V1 = """
resource "aws_db_instance" "payment_db" {
  identifier = "payment-db-prod"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  engine = "postgres"
  username = "dbadmin"
  password = var.db_password
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "payment-cache"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis3.2"
  engine_version       = "3.2.10"
  port                 = 6379
}

resource "aws_s3_bucket" "reports" {
  bucket = "payment-reports-prod-us-east-1"
}

# MATCH: 'payment_db_host' matches 'PAYMENT_DB_HOST' in app.py
output "payment_db_host" {
  value = aws_db_instance.payment_db.address
  description = "The endpoint for the payment database"
}

output "payment_db_port" {
  value = aws_db_instance.payment_db.port
}

output "payment_db_user" {
  value = aws_db_instance.payment_db.username
}

output "redis_primary_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes.0.address
}

output "redis_port" {
  value = aws_elasticache_cluster.redis.port
}

output "report_bucket_name" {
  value = aws_s3_bucket.reports.bucket
}
"""

    # V2: Breaking Change (Renamed Output)
    INFRA_TF_V2_BREAKING = """
resource "aws_db_instance" "payment_db" {
  identifier = "payment-db-prod"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  engine = "postgres"
  username = "dbadmin"
  password = var.db_password
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "payment-cache"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis3.2"
  engine_version       = "3.2.10"
  port                 = 6379
}

resource "aws_s3_bucket" "reports" {
  bucket = "payment-reports-prod-us-east-1"
}

# BREAKING CHANGE: Renamed output. 'PAYMENT_DB_HOST' in app.py will now fail to match.
output "payment_database_endpoint" {
  value = aws_db_instance.payment_db.address
  description = "The endpoint for the payment database"
}

output "payment_db_port" {
  value = aws_db_instance.payment_db.port
}

output "payment_db_user" {
  value = aws_db_instance.payment_db.username
}

output "redis_primary_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes.0.address
}

output "redis_port" {
  value = aws_elasticache_cluster.redis.port
}

output "report_bucket_name" {
  value = aws_s3_bucket.reports.bucket
}
"""

    # Kubernetes manifest
    K8S_YAML = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  template:
    spec:
      containers:
        - name: app
          image: my-app:latest
          env:
            - name: PAYMENT_DB_HOST
              valueFrom:
                secretKeyRef:
                  name: db-secrets
                  key: host
            - name: PAYMENT_DB_PORT
              value: "5432"
            - name: REDIS_PRIMARY_ENDPOINT
              valueFrom:
                configMapKeyRef:
                  name: cache-config
                  key: endpoint
            - name: APP_MAX_RETRIES
              value: "5"
"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def _run_git(self, cwd: Path, args: list[str]) -> None:
        """Run a git command in the demo directory."""
        try:
            subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git command failed: {e}")

    def provision(self) -> Path:
        """
        Create the demo project structure on disk.

        1. Creates baseline files (V1)
        2. Initializes git repo and commits to main
        3. Creates feature branch
        4. Overwrites with breaking change (V2) and commits
        5. Returns path to demo directory
        """
        demo_dir = self.root_dir / "jnkn-demo"
        if demo_dir.exists():
            import shutil

            shutil.rmtree(demo_dir)

        demo_dir.mkdir(exist_ok=True)

        # 1. Create Directories
        src_dir = demo_dir / "src"
        src_dir.mkdir(exist_ok=True)
        tf_dir = demo_dir / "terraform"
        tf_dir.mkdir(exist_ok=True)
        k8s_dir = demo_dir / "k8s"
        k8s_dir.mkdir(exist_ok=True)

        # 2. Write V1 Files (Safe State)
        (src_dir / "app.py").write_text(self.APP_PY.strip())
        (tf_dir / "main.tf").write_text(self.INFRA_TF_V1.strip())
        (k8s_dir / "deployment.yaml").write_text(self.K8S_YAML.strip())

        # 3. Initialize Git & Create Baseline
        self._run_git(demo_dir, ["init", "--initial-branch=main"])
        self._run_git(demo_dir, ["config", "user.email", "demo@jnkn.ai"])
        self._run_git(demo_dir, ["config", "user.name", "Jnkn Demo"])
        self._run_git(demo_dir, ["add", "."])
        self._run_git(demo_dir, ["commit", "-m", "Initial commit: Safe state"])

        # 4. Create Feature Branch
        self._run_git(demo_dir, ["checkout", "-b", "feature/breaking-change"])

        # 5. Introduce Breaking Change
        # Overwrite Terraform with V2 (Renamed output)
        (tf_dir / "main.tf").write_text(self.INFRA_TF_V2_BREAKING.strip())

        # Create CODEOWNERS for reviewer suggestions
        (demo_dir / "CODEOWNERS").write_text(
            """
terraform/  @infra-team
src/        @app-team
k8s/        @platform-team
        """.strip()
        )

        # Commit the breaking change
        self._run_git(demo_dir, ["add", "."])
        self._run_git(demo_dir, ["commit", "-m", "Refactor: Rename database output"])

        return demo_dir
