"""
Unit tests for the CLI Telemetry Middleware.
"""

import click
import pytest
from unittest.mock import patch
from click.testing import CliRunner

from jnkn.cli.utils_telemetry import TelemetryGroup

class TestTelemetryGroup:
    """Test the TelemetryGroup middleware."""

    @pytest.fixture
    def mock_track_event(self):
        """Fixture to mock the telemetry tracking function."""
        with patch("jnkn.cli.utils_telemetry.track_event") as mock:
            yield mock

    def test_successful_command_tracking(self, mock_track_event):
        """Test that a successful command triggers a success event."""
        
        @click.group(cls=TelemetryGroup)
        def cli(): pass

        @cli.command()
        def hello(): click.echo("Hello")

        runner = CliRunner()
        result = runner.invoke(cli, ["hello"])

        assert result.exit_code == 0
        assert mock_track_event.called
        
        props = mock_track_event.call_args.kwargs.get("properties")
        assert props["command"] == "hello"
        assert props["success"] is True
        assert props["exit_code"] == 0

    def test_explicit_exit_code_tracking(self, mock_track_event):
        """
        Test that ctx.exit(10) is captured correctly.
        """
        
        @click.group(cls=TelemetryGroup)
        def cli(): pass

        # FIX: Explicitly name the command to avoid underscore/dash mismatch issues
        @cli.command(name="exit_cmd")
        @click.pass_context
        def exit_cmd(ctx):
            ctx.exit(10)

        runner = CliRunner()
        # Invoke the command
        result = runner.invoke(cli, ["exit_cmd"])

        # 1. Verify the CLI exited with 10. This proves the SystemExit(10) was raised 
        # and bubbled up correctly through the middleware.
        assert result.exit_code == 10
        
        # 2. Verify telemetry was sent
        assert mock_track_event.called
        props = mock_track_event.call_args.kwargs.get("properties")
        assert props["command"] == "exit_cmd"
        assert props["success"] is False
        
        # Verify it captured the exit code. 
        # Note: We assert it matches the result.exit_code to align with runtime reality.
        assert props["exit_code"] == result.exit_code