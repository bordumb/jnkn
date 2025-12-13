# CI Integration

Add Jnkn to your CI pipeline to catch breaking changes on every PR.

## GitHub Actions

Create `.github/workflows/jnkn.yml`:

```yaml
name: Jnkn Impact Analysis

on:
  pull_request:
    paths:
      - '**.py'
      - '**.tf'
      - '**/dbt/**'

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need history for diff
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Jnkn
        run: pip install jnkn
      
      # Zone A: Single command to scan, diff, and report
      - name: Run Jnkn Gate
        run: jnkn check --git-diff origin/${{ github.base_ref }} HEAD --fail-if-critical
```

## What This Does

1. **Triggers** on PRs that modify Python or Terraform files
2. **Scans** your codebase to build the dependency graph
3. **Analyzes** each changed file's blast radius
4. **Reports** results in the GitHub Actions summary

## Example Output

When a PR modifies `terraform/rds.tf`:

```markdown
🚀 Jnkn Impact Analysis

1. Building Dependency Graph...
   Parsed 47 files.
   Stitched 8 cross-domain links.

2. Analyzing Impact (origin/main -> HEAD)...

Summary
This PR modifies 1 infrastructure output impacting 3 downstream consumer(s).

Changes
Artifact                    Type            Change       Blast Radius   Risk
aws_db_instance.payment     infra_resource  ✏️ modified  3              🟠

Analysis Complete: 1 violation found.
  🟠 [HIGH] Change to aws_db_instance.payment impacts 3 downstream artifacts.

Result: WARN
```

<!-- ## Block on High-Risk Changes

Add a failure condition for high-impact changes:

```yaml
- name: Check impact threshold
  run: |
    IMPACT=$(jnkn blast "file://$FILE" --format json | jq '.total_impacted')
    if [ "$IMPACT" -gt 10 ]; then
      echo "::error::High impact change: $IMPACT artifacts affected"
      exit 1
    fi
``` -->

## GitLab CI

See [GitLab CI Integration](../how-to/integration/gitlab-ci.md) for GitLab-specific setup.

<!-- ## Next Steps

- [:octicons-arrow-right-24: Configure confidence thresholds](../how-to/configuration/configure-confidence.md)
- [:octicons-arrow-right-24: Manage suppressions](../how-to/configuration/manage-suppressions.md) -->
