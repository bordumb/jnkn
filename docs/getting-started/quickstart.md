# Quickstart

Scan your first project in 5 minutes.

## 1. Initialize

Navigate to your project root. Jnkan will automatically detect your stack (Python, Terraform, Kubernetes, etc.) and configure itself.

```bash
cd your-project
jnkn init
```

This creates `.jnkn/config.yaml` with sensible defaults.

## 2. Check

Run a check to see if your current changes break any downstream dependencies. This command automatically scans your project, builds the graph, and compares your current state against `main`.

```bash
jnkn check
```

Output:

```
🚀 Jnkn Impact Analysis
   Scan Dir: /path/to/your-project

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

<!-- ## 3. Explore

### View Statistics

```bash
jnkn stats
```

```
📊 Graph Statistics
═══════════════════════════════════
Nodes:     156
Edges:     97
Files:     47

By Type:
  code_file:       42
  env_var:         12
  infra_resource:  8
```

### Calculate Blast Radius

```bash
jnkn blast env:DATABASE_URL
```

```json
{
  "source": "env:DATABASE_URL",
  "total_impacted": 3,
  "impacted": [
    "file://src/db/connection.py",
    "file://src/api/users.py",
    "infra:aws_db_instance.main"
  ]
}
```

### Explain a Match

```bash
jnkn explain env:DB_HOST infra:db_host
```

```
Source: env:DB_HOST → Tokens: [db, host]
Target: infra:db_host → Tokens: [db, host]

Confidence: 0.85 (HIGH)
  [+0.90] normalized_match: 'dbhost' == 'dbhost'
  [×0.95] penalty: short token 'db'
``` -->

## What Just Happened?

1. **Parse**: Jnkn scanned your Python and Terraform files
2. **Extract**: Found environment variables and infrastructure resources  
3. **Stitch**: Linked `env:DATABASE_URL` to `infra:aws_db_instance.main` via token matching
4. **Store**: Saved the graph to `.jnkn/jnkn.db`

<!-- ## Common Issues

??? question "No env vars found"
    
    Jnkn looks for specific patterns. Check [Supported Patterns](../reference/patterns/index.md) to ensure your code matches.

??? question "Too many false positives"
    
    Lower the confidence threshold or add suppressions:
    
    ```bash
    jnkn suppress add "env:*_ID" "infra:*" --reason "ID fields are generic"
    ``` -->

## Next Steps

- [:octicons-arrow-right-24: Set up CI integration](first-ci-integration.md)
<!-- - [:octicons-arrow-right-24: Learn about blast radius](../explanation/concepts/blast-radius.md)
- [:octicons-arrow-right-24: Configure confidence thresholds](../how-to/configuration/configure-confidence.md) -->
