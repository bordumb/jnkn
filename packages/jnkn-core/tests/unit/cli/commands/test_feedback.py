"""
Unit tests for the 'feedback' command.
"""

from unittest.mock import patch
from click.testing import CliRunner
from jnkn.cli.commands.feedback import feedback

class TestFeedbackCommand:
    """Test the feedback command."""

    @patch("jnkn.cli.commands.feedback.webbrowser.open")
    def test_feedback_opens_browser(self, mock_browser):
        """Test that the command constructs a URL and opens the browser."""
        runner = CliRunner()
        result = runner.invoke(feedback)
        
        assert result.exit_code == 0
        assert "Opening feedback form" in result.output
        
        # Verify browser call
        assert mock_browser.called
        url = mock_browser.call_args[0][0]
        
        # Verify URL structure
        assert "github.com/bordumb/jnkn/issues/new" in url
        assert "labels=feedback" in url
        
        # Verify system info is present in the body
        # URL encoded check for 'System Information'
        assert "System+Information" in url or "System%20Information" in url
        assert "Jnkn+Version" in url or "Jnkn%20Version" in url

    @patch("jnkn.cli.commands.feedback.webbrowser.open")
    def test_feedback_includes_python_version(self, mock_browser):
        """Verify dynamic system info (Python version) is included."""
        import sys
        current_py_version = sys.version.split()[0]
        
        runner = CliRunner()
        runner.invoke(feedback)
        
        url = mock_browser.call_args[0][0]
        # Check that the current python version is embedded in the URL
        assert current_py_version in url