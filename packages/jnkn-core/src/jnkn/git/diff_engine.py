"""
Git Diff Engine.

Provides actual git integration for determining what changed between refs.
Works in both local development and CI environments.
"""

import logging
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class FileStatus(StrEnum):
    """Git file status codes."""

    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNTRACKED = "?"


@dataclass
class ChangedFile:
    """A file that changed between two refs."""

    path: str
    status: FileStatus
    old_path: Optional[str] = None  # For renames

    @property
    def is_deleted(self) -> bool:
        return self.status == FileStatus.DELETED

    @property
    def is_added(self) -> bool:
        return self.status == FileStatus.ADDED


class GitError(Exception):
    """Raised when a git command fails."""

    def __init__(self, message: str, stderr: str = ""):
        self.message = message
        self.stderr = stderr
        super().__init__(f"{message}: {stderr}" if stderr else message)


class GitDiffEngine:
    """
    Extracts diff information from git.

    Works in multiple environments:
    - Local development (comparing working tree to branch)
    - GitHub Actions (comparing PR head to base)
    - GitLab CI (comparing merge request source to target)
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._validate_git_repo()

    def _validate_git_repo(self) -> None:
        """Ensure we're in a git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise GitError(f"Not a git repository: {self.repo_path}")

    def _run_git(self, *args: str) -> str:
        """Run a git command and return stdout."""
        cmd = ["git", "-C", str(self.repo_path)] + list(args)
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {' '.join(args)}", e.stderr.strip())

    def get_changed_files(self, base_ref: str, head_ref: str = "HEAD") -> List[ChangedFile]:
        """
        Get list of files changed between two refs.

        Args:
            base_ref: Base reference (e.g., "origin/main", "main", commit SHA)
            head_ref: Head reference (e.g., "HEAD", branch name)

        Returns:
            List of ChangedFile objects
        """
        # Ensure refs exist
        self._ensure_ref_exists(base_ref)
        self._ensure_ref_exists(head_ref)

        # Get diff with status codes
        # --name-status gives us: STATUS\tFILENAME (or STATUS\tOLD\tNEW for renames)
        output = self._run_git(
            "diff",
            "--name-status",
            f"{base_ref}...{head_ref}",  # Three dots = merge-base comparison
        )

        if not output:
            return []

        changed_files = []
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue

            status_code = parts[0][0]  # First char (R100 -> R)

            try:
                status = FileStatus(status_code)
            except ValueError:
                logger.warning(f"Unknown git status code: {status_code}")
                status = FileStatus.MODIFIED

            if status in (FileStatus.RENAMED, FileStatus.COPIED) and len(parts) >= 3:
                # Rename: R100\told_path\tnew_path
                changed_files.append(
                    ChangedFile(
                        path=parts[2],
                        status=status,
                        old_path=parts[1],
                    )
                )
            else:
                changed_files.append(
                    ChangedFile(
                        path=parts[1],
                        status=status,
                    )
                )

        return changed_files

    def _ensure_ref_exists(self, ref: str) -> None:
        """
        Ensure a git ref exists, fetching if necessary.

        This handles CI environments where refs may not be fetched yet.
        """
        try:
            self._run_git("rev-parse", "--verify", ref)
        except GitError:
            # Try to fetch it
            logger.info(f"Ref '{ref}' not found locally, attempting to fetch...")

            # Extract remote and branch from ref like "origin/main"
            if "/" in ref:
                remote, branch = ref.split("/", 1)
                try:
                    self._run_git("fetch", remote, branch)
                except GitError as e:
                    raise GitError(
                        f"Could not access ref '{ref}'. Ensure it exists and has been fetched.",
                        e.stderr,
                    )
            else:
                raise GitError(f"Ref '{ref}' not found and cannot be fetched")

    def get_merge_base(self, ref1: str, ref2: str) -> str:
        """Get the merge base commit between two refs."""
        return self._run_git("merge-base", ref1, ref2)

    def get_file_content_at_ref(self, ref: str, file_path: str) -> Optional[str]:
        """
        Get the content of a file at a specific ref.

        Returns None if file doesn't exist at that ref.
        """
        try:
            return self._run_git("show", f"{ref}:{file_path}")
        except GitError:
            return None

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            return self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        except GitError:
            return "HEAD"

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        """Check if ancestor is an ancestor of descendant."""
        try:
            self._run_git("merge-base", "--is-ancestor", ancestor, descendant)
            return True
        except GitError:
            return False
