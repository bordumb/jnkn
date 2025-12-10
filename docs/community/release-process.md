
# Release Process

This document outlines the steps required to publish a new version of `jnkn` to PyPI and update the documentation site.

## Versioning Strategy

`jnkn` follows [Semantic Versioning 2.0.0](https://semver.org/):

* **MAJOR** version when you make incompatible API changes.
* **MINOR** version when you add functionality in a backward-compatible manner.
* **PATCH** version when you make backward-compatible bug fixes.

**Pre-releases:**
For beta or release candidates, append a suffix like `-beta.1` or `-rc.1`.
* Example: `0.5.0-rc.1`

## Prerequisites

To perform a release, you must have:

1.  **Write access** to the [GitHub repository](https://github.com/jnkn-io/jnkn).
2.  **Admin access** on [PyPI](https://pypi.org/project/jnkn/) (or be part of the trusted publisher workflow).

## Step-by-Step Guide

### 1. Prepare the Release

Before tagging, ensure the codebase is ready.

1.  **Update the Changelog:**
    Edit `docs/changelog/CHANGELOG.md` to move "Unreleased" changes into a new version header.

2.  **Bump the Version:**
    Update the `version` field in `pyproject.toml`.
    ```toml
    [project]
    name = "jnkn"
    version = "0.6.0"  # <--- Update this
    ```

3.  **Commit the Changes:**
    ```bash
    git add pyproject.toml docs/changelog/CHANGELOG.md
    git commit -m "chore: bump version to 0.6.0"
    ```

### 2. Tag and Push

Create a git tag for the version. The tag **must** match the version in `pyproject.toml`.

```bash
# Create an annotated tag
git tag -a v0.6.0 -m "Release v0.6.0"

# Push the commit and the tag
git push origin main --follow-tags
````

### 3\. Create GitHub Release

This is the trigger for our deployment pipeline.

1.  Go to the [Releases page](https://github.com/bordumb/jnkn/releases) on GitHub.
2.  Click **Draft a new release**.
3.  **Choose a tag:** Select the tag you just pushed (`v0.6.0`).
4.  **Release title:** Use the version number (`v0.6.0`).
5.  **Description:** Click "Generate release notes" to auto-populate from PRs, or paste the relevant section from your `CHANGELOG.md`.
6.  Click **Publish release**.

-----

## Automated Pipeline

Once you click "Publish release", GitHub Actions takes over.

### 1\. PyPI Publication

  * **Workflow:** `.github/workflows/pypi-publish.yml`
  * **Trigger:** Release published.
  * **Action:**
      * Builds the package using `uv build`.
      * Authenticates with PyPI using OIDC (Trusted Publishing).
      * Uploads the `.whl` and `.tar.gz` files to PyPI.

### 2\. Documentation Deployment

  * **Workflow:** `.github/workflows/docs-deploy.yml`
  * **Trigger:** Push to `main` (which happened in Step 2) or Release.
  * **Action:**
      * Installs documentation dependencies.
      * Builds the MkDocs site.
      * Deploys the static HTML to the `gh-pages` branch.
      * Updates the `latest` version alias.

-----

## Verification

After the pipelines complete (usually \~2-3 minutes), verify the release:

1.  **PyPI:** Check [pypi.org/project/jnkn/](https://pypi.org/project/jnkn/) to see the new version.
2.  **Installation:** Run `pip install --upgrade jnkn` locally to ensure it installs correctly.
3.  **Docs:** Visit [docs.jnkn.io](https://docs.jnkn.io) and ensure the version dropdown (if enabled) or the changelog reflects the update.
