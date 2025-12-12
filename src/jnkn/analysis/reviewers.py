"""
Reviewer Suggestion Engine.

Suggests reviewers based on:
1. CODEOWNERS file (if present)
2. Git blame for changed files
3. Directory ownership heuristics
"""

import logging
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class SuggestedReviewer:
    """A suggested reviewer with reasoning."""

    username: str
    reason: str
    score: int  # Relevance (higher = more relevant)
    files: List[str] = None  # Files they should review

    def __post_init__(self):
        if self.files is None:
            self.files = []

    def to_dict(self):
        return {
            "username": self.username,
            "reason": self.reason,
            "score": self.score,
            "files": self.files,
        }


class ReviewerSuggester:
    """
    Suggests reviewers for changed files.
    """

    def __init__(self, repo_path: Path, use_git_blame: bool = True):
        self.repo_path = repo_path
        self.use_git_blame = use_git_blame
        self.codeowners_rules = self._load_codeowners()

    def suggest(
        self,
        affected_files: List[str],
        max_reviewers: int = 5,
    ) -> List[SuggestedReviewer]:
        """
        Suggest reviewers for a list of affected files.

        Args:
            affected_files: List of file paths (relative to repo root)
            max_reviewers: Maximum number of reviewers to suggest

        Returns:
            List of SuggestedReviewer sorted by relevance
        """
        suggestions: Dict[str, SuggestedReviewer] = {}

        for file_path in affected_files:
            # 1. Check CODEOWNERS
            owners = self._find_codeowners(file_path)
            for owner in owners:
                self._add_suggestion(
                    suggestions,
                    owner,
                    f"CODEOWNERS for {file_path}",
                    score=10,  # CODEOWNERS is authoritative
                    file_path=file_path,
                )

            # 2. Git blame (if enabled and no CODEOWNERS match)
            if self.use_git_blame and not owners:
                blame_authors = self._get_blame_authors(file_path)
                for author, count in blame_authors.most_common(3):
                    self._add_suggestion(
                        suggestions,
                        author,
                        f"Recent contributor to {file_path}",
                        score=count,  # More lines = higher score
                        file_path=file_path,
                    )

        # 3. Apply directory heuristics if still no suggestions
        if not suggestions:
            self._apply_heuristics(affected_files, suggestions)

        # Sort by score and return top N
        sorted_suggestions = sorted(suggestions.values(), key=lambda x: x.score, reverse=True)

        return sorted_suggestions[:max_reviewers]

    def _add_suggestion(
        self,
        suggestions: Dict[str, SuggestedReviewer],
        username: str,
        reason: str,
        score: int,
        file_path: str,
    ) -> None:
        """Add or update a suggestion."""
        # Normalize username
        username = username.strip()
        if not username or username.startswith("#"):
            return

        # NEW: Automatically prepend @ if it looks like a handle (no spaces)
        # This makes 'bordumb' -> '@bordumb' so it hyperlinks in PR comments
        if " " not in username and not username.startswith("@"):
            username = f"@{username}"

        if username in suggestions:
            suggestions[username].score += score
            if file_path not in suggestions[username].files:
                suggestions[username].files.append(file_path)
        else:
            suggestions[username] = SuggestedReviewer(
                username=username,
                reason=reason,
                score=score,
                files=[file_path],
            )

    def _load_codeowners(self) -> List[tuple]:
        """Load and parse CODEOWNERS file."""
        locations = [
            self.repo_path / ".github" / "CODEOWNERS",
            self.repo_path / "CODEOWNERS",
            self.repo_path / "docs" / "CODEOWNERS",
        ]

        rules = []

        for loc in locations:
            if loc.exists():
                try:
                    content = loc.read_text()
                    for line in content.splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue

                        parts = line.split()
                        if len(parts) < 2:
                            continue

                        pattern = parts[0]
                        owners = parts[1:]

                        # Convert glob to regex
                        regex = self._glob_to_regex(pattern)
                        rules.append((re.compile(regex), owners))

                    logger.debug(f"Loaded {len(rules)} CODEOWNERS rules from {loc}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to parse CODEOWNERS at {loc}: {e}")

        return rules

    def _glob_to_regex(self, glob: str) -> str:
        """
        Convert CODEOWNERS glob pattern to regex.

        Handles:
        - * matches any characters except slash
        - ** matches any characters including slash
        - trailing / implies /**
        - leading / anchors to root
        """
        pattern = glob.strip()

        # 1. Handle directory patterns (ending in /)
        # /infra/ -> /infra/**
        if pattern.endswith("/"):
            pattern += "**"

        # 2. Use placeholders to preserve glob characters during escape
        chars = {
            "**": "__DS__",
            "*": "__SS__",
            "?": "__QM__",
        }

        for k, v in chars.items():
            pattern = pattern.replace(k, v)

        # Escape everything else (dots, brackets, etc)
        pattern = re.escape(pattern)

        # 3. Replace placeholders with regex logic
        pattern = pattern.replace("__DS__\\/", r"(?:.*/)?")
        pattern = pattern.replace("__DS__/", r"(?:.*/)?")
        pattern = pattern.replace("__DS__", r".*")
        pattern = pattern.replace("__SS__", r"[^/]*")
        pattern = pattern.replace("__QM__", r".")

        # 4. Handle Anchoring
        if pattern.startswith("/") or pattern.startswith(r"\/"):
            if pattern.startswith(r"\/"):
                pattern = pattern[2:]
            else:
                pattern = pattern[1:]
            pattern = f"^{pattern}"
        else:
            pattern = f"(?:^|/){pattern}"

        # 5. Handle Trailing Boundary
        pattern = f"{pattern}(?:$|/)"

        return pattern

    def _find_codeowners(self, file_path: str) -> List[str]:
        """Find CODEOWNERS for a file. Last match wins."""
        matching_owners = []
        clean_path = str(file_path).lstrip("./")

        for pattern, owners in self.codeowners_rules:
            if pattern.search(clean_path):
                matching_owners = owners

        return matching_owners

    def _get_blame_authors(self, file_path: str, max_lines: int = 100) -> Counter:
        """Get authors from git blame for a file."""
        authors: Counter = Counter()

        full_path = self.repo_path / file_path
        if not full_path.exists():
            return authors

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.repo_path),
                    "blame",
                    "--line-porcelain",
                    "-L",
                    f"1,{max_lines}",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("author "):
                        author = line[7:].strip()
                        if author and author != "Not Committed Yet":
                            authors[author] += 1
        except Exception as e:
            logger.debug(f"Git blame failed for {file_path}: {e}")

        return authors

    def _apply_heuristics(
        self, files: List[str], suggestions: Dict[str, SuggestedReviewer]
    ) -> None:
        """Apply directory-based heuristics when no owners found."""
        directory_teams = {
            "terraform": "@platform-team",
            "infra": "@platform-team",
            "k8s": "@platform-team",
            "kubernetes": "@platform-team",
            "src/data": "@data-team",
            "dbt": "@data-team",
            "pipelines": "@data-team",
        }

        seen_teams: Set[str] = set()

        for file_path in files:
            path = Path(file_path)
            for dir_pattern, team in directory_teams.items():
                if file_path.startswith(dir_pattern) and team not in seen_teams:
                    seen_teams.add(team)
                    self._add_suggestion(
                        suggestions,
                        team,
                        f"Team owns {dir_pattern}/ directory",
                        score=5,
                        file_path=file_path,
                    )
