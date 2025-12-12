"""
Unit tests for the Reviewer Suggestion Engine.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jnkn.analysis.reviewers import ReviewerSuggester, SuggestedReviewer


@pytest.fixture
def mock_repo_path(tmp_path):
    """Create a temporary repo path."""
    return tmp_path


@pytest.fixture
def suggester(mock_repo_path):
    """Create a ReviewerSuggester instance with mocked CODEOWNERS loading."""
    with patch.object(ReviewerSuggester, "_load_codeowners", return_value=[]):
        return ReviewerSuggester(mock_repo_path)


class TestReviewerSuggester:
    """Tests for ReviewerSuggester logic."""

    def test_glob_to_regex_conversion(self, suggester):
        """Test conversion of glob patterns to regex."""
        # Simple wildcard
        regex = suggester._glob_to_regex("*.js")
        assert re.match(regex, "app.js")
        assert not re.match(regex, "app.py")

        # Directory wildcard
        regex = suggester._glob_to_regex("docs/*")
        assert re.match(regex, "docs/index.md")
        assert not re.match(regex, "src/main.py")

        # Double star (recursive)
        regex = suggester._glob_to_regex("src/**/*.py")
        assert re.match(regex, "src/utils/helper.py")
        assert re.match(regex, "src/main.py")
        assert not re.match(regex, "src/README.md")

        # Root anchor
        regex = suggester._glob_to_regex("/build/logs/")
        assert re.match(regex, "build/logs/error.log")
        assert not re.match(regex, "foo/build/logs/error.log")

    def test_find_codeowners(self, suggester):
        """Test matching files against loaded CODEOWNERS rules."""
        # Manually inject rules
        suggester.codeowners_rules = [
            (re.compile(suggester._glob_to_regex("*.js")), ["@frontend"]),
            (re.compile(suggester._glob_to_regex("docs/*")), ["@writers"]),
            (re.compile(suggester._glob_to_regex("/infra/")), ["@devops"]),
        ]

        assert suggester._find_codeowners("app.js") == ["@frontend"]
        assert suggester._find_codeowners("docs/api.md") == ["@writers"]
        assert suggester._find_codeowners("infra/main.tf") == ["@devops"]
        assert suggester._find_codeowners("unknown.py") == []

    @patch("subprocess.run")
    def test_git_blame_suggestions(self, mock_run, suggester):
        """Test suggestions derived from git blame."""
        # Mock git blame output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
author alice@example.com
author-mail <alice@example.com>
author-time 1600000000
summary First commit
filename file.py
        
author bob@example.com
author-mail <bob@example.com>
author-time 1600000001
summary Fix bug
filename file.py

author alice@example.com
author-mail <alice@example.com>
author-time 1600000002
summary Update
filename file.py
        """

        # Mock file existence check
        with patch.object(Path, "exists", return_value=True):
            suggestions = suggester.suggest(["file.py"])

        assert len(suggestions) >= 2
        # Alice appears twice, Bob once
        alice = next(s for s in suggestions if s.username == "alice@example.com")
        bob = next(s for s in suggestions if s.username == "bob@example.com")

        assert alice.score > bob.score
        assert "Recent contributor" in alice.reason

    def test_directory_heuristics(self, suggester):
        """Test fallback suggestions based on directory names."""
        files = ["terraform/main.tf", "src/data/models.py"]
        
        suggestions = suggester.suggest(files)
        
        # Should match built-in heuristics
        platform_team = next((s for s in suggestions if s.username == "@platform-team"), None)
        data_team = next((s for s in suggestions if s.username == "@data-team"), None)
        
        assert platform_team is not None
        assert "terraform" in platform_team.reason
        
        assert data_team is not None
        assert "src/data" in data_team.reason

    def test_add_suggestion_logic(self, suggester):
        """Test scoring and merging of suggestions."""
        suggestions = {}
        
        # First hit
        suggester._add_suggestion(suggestions, "@alice", "Reason 1", 5, "file1.py")
        assert suggestions["@alice"].score == 5
        assert suggestions["@alice"].files == ["file1.py"]
        
        # Second hit (different file)
        suggester._add_suggestion(suggestions, "@alice", "Reason 2", 3, "file2.py")
        assert suggestions["@alice"].score == 8  # Scores sum up
        assert len(suggestions["@alice"].files) == 2
        
        # Ignore empty or commented usernames
        suggester._add_suggestion(suggestions, "", "Bad", 1, "f.py")
        suggester._add_suggestion(suggestions, "#comment", "Bad", 1, "f.py")
        assert len(suggestions) == 1

    def test_load_codeowners_file_parsing(self, mock_repo_path):
        """Test parsing of actual CODEOWNERS file content."""
        codeowners_file = mock_repo_path / "CODEOWNERS"
        codeowners_file.write_text("""
# This is a comment
*.js       @js-owner
docs/* @docs-owner @editor
/build/    @build-bot
        """)
        
        # Re-initialize to trigger real loading
        suggester = ReviewerSuggester(mock_repo_path)
        
        assert len(suggester.codeowners_rules) == 3
        
        # Check rule 1
        regex, owners = suggester.codeowners_rules[0]
        assert owners == ["@js-owner"]
        assert regex.search("main.js")
        
        # Check rule 2 (multiple owners)
        regex, owners = suggester.codeowners_rules[1]
        assert owners == ["@docs-owner", "@editor"]
        assert regex.search("docs/readme.txt")