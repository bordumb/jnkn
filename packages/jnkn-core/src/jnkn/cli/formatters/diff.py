"""
Diff Formatters.

Creates manager-readable output for:
1. Terminal (Rich-based)
2. GitHub PR comments (Markdown)
3. JSON (for API/CI integration)
"""

from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...analysis.diff_analyzer import ChangeType, DiffReport
from ...analysis.reviewers import SuggestedReviewer
from ...analysis.risk import RiskAssessment
from ...core.types import NodeType


class DiffFormatter:
    """Formats diff analysis results."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    # =========================================================================
    # Terminal Output
    # =========================================================================

    def print_summary(
        self,
        report: DiffReport,
        risk: RiskAssessment,
        reviewers: List[SuggestedReviewer],
    ) -> None:
        """Print manager-readable summary to terminal."""
        self.console.print()

        # 1. Risk Header
        self._print_risk_panel(risk)

        # 2. Executive Summary
        self._print_executive_summary(report, risk)

        # 3. Changes Table
        if report.node_changes:
            self._print_changes_table(report)

        # 4. Suggested Reviewers
        if reviewers:
            self._print_reviewers(reviewers)

        self.console.print()

    def _print_risk_panel(self, risk: RiskAssessment) -> None:
        """Print the risk score panel."""
        self.console.print(
            Panel(
                f"[bold {risk.color}]{risk.icon} Risk Level: {risk.level.value}[/bold {risk.color}]\n"
                f"Safety Score: [{risk.color}]{risk.score}/100[/{risk.color}]",
                border_style=risk.color,
                expand=False,
                title="Impact Analysis",
            )
        )

    def _print_executive_summary(self, report: DiffReport, risk: RiskAssessment) -> None:
        """Print the executive summary."""
        self.console.print("\n[bold]Summary[/bold]")

        # Count by type
        infra_changes = len(report.get_changes_by_type(NodeType.INFRA_RESOURCE))
        env_changes = len(report.get_changes_by_type(NodeType.ENV_VAR))

        parts = []
        if infra_changes:
            parts.append(f"[bold]{infra_changes}[/bold] infrastructure output(s)")
        if env_changes:
            parts.append(f"[bold]{env_changes}[/bold] environment variable(s)")
        if report.files_changed:
            parts.append(f"[bold]{report.files_changed}[/bold] file(s)")

        if parts:
            self.console.print(f"This PR modifies {', '.join(parts)}.")

        # Blast radius summary
        total_blast = sum(c.blast_radius for c in report.node_changes)
        if total_blast > 0:
            self.console.print(
                f"Total downstream impact: [bold]{total_blast}[/bold] consumer(s) affected."
            )

        if risk.summary:
            self.console.print(f"[dim]{risk.summary}[/dim]")

    def _print_changes_table(self, report: DiffReport) -> None:
        """Print changes in a table."""
        self.console.print("\n[bold]Changes[/bold]")

        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Artifact", style="cyan")
        table.add_column("Type")
        table.add_column("Change")
        table.add_column("Blast Radius", justify="right")
        table.add_column("Risk")

        # Sort: removed first, then modified, then added
        for change in report.node_changes[:15]:  # Limit display
            change_icon = {
                ChangeType.REMOVED: "🗑️",
                ChangeType.MODIFIED: "✏️",
                ChangeType.ADDED: "➕",
            }.get(change.change_type, "•")

            change_style = {
                ChangeType.REMOVED: "red",
                ChangeType.MODIFIED: "yellow",
                ChangeType.ADDED: "green",
            }.get(change.change_type, "white")

            table.add_row(
                change.name,
                change.type.value,
                f"[{change_style}]{change_icon} {change.change_type.value}[/{change_style}]",
                str(change.blast_radius) if change.blast_radius else "-",
                change.risk_indicator,
            )

        self.console.print(table)

        if len(report.node_changes) > 15:
            self.console.print(f"[dim]... and {len(report.node_changes) - 15} more changes[/dim]")

    def _print_reviewers(self, reviewers: List[SuggestedReviewer]) -> None:
        """Print suggested reviewers."""
        self.console.print("\n[bold]🔧 Suggested Reviewers[/bold]")
        for r in reviewers[:5]:
            self.console.print(f"  • [cyan]{r.username}[/cyan] - {r.reason}")

    # =========================================================================
    # Markdown Output (for GitHub PR comments)
    # =========================================================================

    def generate_markdown(
        self,
        report: DiffReport,
        risk: RiskAssessment,
        reviewers: List[SuggestedReviewer],
    ) -> str:
        """Generate GitHub PR comment markdown."""
        lines = []

        # Header
        lines.append("## 🔍 Jnkn Impact Analysis")
        lines.append("")
        lines.append(f"### Risk Level: {risk.icon} {risk.level.value} (Score: {risk.score}/100)")
        lines.append("")

        # Summary
        lines.append("### Summary")
        lines.append(self._generate_summary_text(report))
        lines.append("")

        # Changes Table
        if report.node_changes:
            lines.append("| Changed | Type | Blast Radius | Risk |")
            lines.append("|---------|------|--------------|------|")

            for change in report.node_changes[:10]:
                name = f"`{change.name}`"
                type_name = change.type.value
                blast = str(change.blast_radius) if change.blast_radius else "-"
                risk_icon = change.risk_indicator

                lines.append(f"| {name} | {type_name} | {blast} consumers | {risk_icon} |")

            if len(report.node_changes) > 10:
                lines.append(f"| ... | {len(report.node_changes) - 10} more | | |")

            lines.append("")

        # Required Actions
        lines.append("### 🎯 Required Actions")
        lines.extend(self._generate_required_actions(report))
        lines.append("")

        # Dependency Tree (collapsible)
        if report.node_changes:
            lines.append("<details>")
            lines.append(
                f"<summary>📊 Full Dependency Tree ({len(report.node_changes)} nodes)</summary>"
            )
            lines.append("")
            lines.append("```")
            for change in report.node_changes[:20]:
                prefix = "├──" if change != report.node_changes[-1] else "└──"
                status = {"added": "+", "removed": "-", "modified": "~"}.get(
                    change.change_type.value, " "
                )
                lines.append(f"{prefix} [{status}] {change.name} ({change.type.value})")
            lines.append("```")
            lines.append("</details>")
            lines.append("")

        # Suggested Reviewers (collapsible)
        if reviewers:
            lines.append("<details>")
            lines.append("<summary>🔧 Suggested Reviewers</summary>")
            lines.append("")
            lines.append("Based on code ownership of affected files:")
            lines.append("")
            for r in reviewers[:5]:
                lines.append(f"- **{r.username}** - {r.reason}")
            lines.append("")
            lines.append("</details>")

        return "\n".join(lines)

    def _generate_summary_text(self, report: DiffReport) -> str:
        """Generate summary text for markdown."""
        parts = []

        infra = len(report.get_changes_by_type(NodeType.INFRA_RESOURCE))
        env = len(report.get_changes_by_type(NodeType.ENV_VAR))

        if infra:
            parts.append(f"**{infra} Terraform output(s)**")
        if env:
            parts.append(f"**{env} environment variable(s)**")

        if not parts:
            parts.append(f"**{report.total_changes} artifact(s)**")

        total_blast = sum(c.blast_radius for c in report.node_changes)

        text = f"This PR modifies {' and '.join(parts)}"
        if total_blast > 0:
            text += f" impacting **{total_blast} downstream consumer(s)**"
        text += "."

        return text

    def _generate_required_actions(self, report: DiffReport) -> List[str]:
        """Generate required action checkboxes."""
        actions = []

        # Check for infra changes
        infra_changes = report.get_changes_by_type(NodeType.INFRA_RESOURCE)
        if infra_changes:
            for change in infra_changes[:3]:
                if change.blast_radius > 0:
                    actions.append(f"- [ ] Verify consumers of `{change.name}` handle this change")

        # Check for removed items
        for change in report.removed_nodes[:3]:
            actions.append(f"- [ ] Confirm `{change.name}` removal won't break downstream services")

        # Check for env var changes
        env_changes = report.get_changes_by_type(NodeType.ENV_VAR)
        if env_changes:
            actions.append(
                "- [ ] Update deployment manifests if environment variable names changed"
            )

        # Default if nothing specific
        if not actions:
            actions.append("- [ ] Review impact on downstream dependencies")

        return actions
