# Setup Guide for CI/CD Pipeline

This guide will help you configure the comprehensive CI/CD pipeline for pymbrewclient.

**Currently in use by:** [stuartp44/pymbrewclient](https://github.com/stuartp44/pymbrewclient)

## Overview

The pipeline includes:
1. **PR Acknowledgment** - Automatically thanks contributors
2. **Semantic Versioning** - Auto-versioning based on commit messages
3. **Automated Testing** - Runs on every PR and push
4. **Automated Releases** - Creates GitHub releases and publishes to PyPI
5. **Changelog Generation** - Automatically generates CHANGELOG.md

## Prerequisites

Before the pipeline can work, you need to configure:

### 1. PyPI Publishing (Required for releases)

The project uses PyPI's Trusted Publishers (OIDC) for secure publishing without API tokens.

**Steps:**

1. Go to [PyPI](https://pypi.org/) and log in
2. Navigate to your project (or create it if it doesn't exist)
3. Go to "Publishing" → "Add a new publisher"
4. Fill in:
   - **PyPI Project Name**: `pymbrewclient`
   - **Owner**: `stuartp44`
   - **Repository name**: `pymbrewclient`
   - **Workflow name**: `semantic-release.yml`
   - **Environment name**: Leave empty (not using environments)

**Alternative (using API token):**

If you prefer using an API token:
1. Generate a PyPI API token
2. Add it as a GitHub secret named `PYPI_API_TOKEN`
3. Update [.github/workflows/semantic-release.yml](.github/workflows/semantic-release.yml):
   ```yaml
   - name: Publish to PyPI
     if: env.NEW_VERSION != ''
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

### 2. GitHub Permissions

The workflows need specific permissions that are already configured in the workflow files:
- `contents: write` - For creating releases and updating CHANGELOG
- `pull-requests: write` - For PR comments
- `id-token: write` - For OIDC authentication with PyPI

Ensure your repository settings allow GitHub Actions to:
1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **Read and write permissions**
3. Check **Allow GitHub Actions to create and approve pull requests**

### 3. Branch Protection (Recommended)

Protect the `main` branch:
1. Go to **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Enable:
   - Require a pull request before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging
   - Select status checks: `test`, `lint`, `build`, `check-pr-title`

## How It Works

### Workflow Triggers

#### 1. **PR Acknowledgment** ([.github/workflows/pr-acknowledgment.yml](.github/workflows/pr-acknowledgment.yml))
- **Trigger**: When a PR is opened
- **Actions**:
  - Posts a welcome comment thanking the contributor
  - Adds special message for first-time contributors
  - Adds labels: `needs-review`, `first-time-contributor`

#### 2. **Test and Build** ([.github/workflows/test-and-release.yml](.github/workflows/test-and-release.yml))
- **Trigger**: On every PR and push to main
- **Actions**:
  - Runs pytest with coverage
  - Runs linting (ruff, black)
  - Builds the package
  - Validates the build with twine

#### 3. **Semantic PR Title Check** ([.github/workflows/semantic-pr.yml](.github/workflows/semantic-pr.yml))
- **Trigger**: When PR is opened/updated
- **Actions**:
  - Validates PR title follows Conventional Commits
  - Blocks merge if title is invalid

#### 4. **Semantic Release** ([.github/workflows/semantic-release.yml](.github/workflows/semantic-release.yml))
- **Trigger**: When commits are pushed to `main`
- **Actions**:
  - Analyzes commits since last release
  - Determines next version number
  - Generates CHANGELOG.md
  - Creates Git tag
  - Creates GitHub release with notes
  - Builds Python package
  - Publishes to PyPI

### Commit Message Format

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Version Bumps:**
- `feat:` → Minor version (0.X.0)
- `fix:`, `perf:`, `refactor:` → Patch version (0.0.X)
- `feat!:` or `BREAKING CHANGE:` → Major version (X.0.0)

**Examples:**
```bash
feat(cli): add JSON output format
fix(client): handle timeout errors
docs: update README with examples
feat(api)!: redesign authentication

BREAKING CHANGE: Authentication now requires API tokens
```

See [.github/COMMIT_CONVENTION.md](.github/COMMIT_CONVENTION.md) for details.

## Release Process

### Automatic Releases

Releases happen automatically when commits are merged to `main`:

1. **Make changes** in a feature branch
2. **Create PR** with semantic title (e.g., `feat: add new feature`)
3. **Get approval** from maintainer
4. **Merge to main**
5. **Semantic Release workflow runs** and:
   - Analyzes commits
   - Bumps version
   - Updates CHANGELOG.md
   - Creates GitHub release
   - Publishes to PyPI

### Manual Release (if needed)

You can trigger a release manually:

1. Go to **Actions** → **Semantic Release**
2. Click **Run workflow**
3. Select `main` branch
4. Click **Run workflow**

## First Release

For the first release after setting up this pipeline:

1. Ensure all changes are committed and pushed
2. Merge a commit with type `feat:` to trigger initial release:
   ```bash
   git checkout main
   git commit --allow-empty -m "feat: initialize semantic release"
   git push
   ```
3. The workflow will create version `1.0.0` (or the appropriate version based on commit history)

## Version Management

The project uses `setuptools_scm` for version management, which gets the version from Git tags. After semantic-release creates a tag, setuptools_scm will use it automatically.

## Troubleshooting

### Release didn't trigger
- Check that commits follow Conventional Commits format
- Verify workflow permissions are set correctly
- Check workflow logs in Actions tab

### PyPI publish failed
- Verify OIDC publisher is configured correctly on PyPI
- Check that package name matches exactly: `pymbrewclient`
- Ensure the version doesn't already exist on PyPI

### PR checks failing
- Run tests locally: `pytest`
- Check linting: `ruff check .` and `black --check .`
- Verify PR title follows semantic format

## Files Created

The pipeline consists of:

- **Workflows:**
  - [.github/workflows/pr-acknowledgment.yml](.github/workflows/pr-acknowledgment.yml) - PR welcome bot
  - [.github/workflows/semantic-release.yml](.github/workflows/semantic-release.yml) - Automated releases
  - [.github/workflows/semantic-pr.yml](.github/workflows/semantic-pr.yml) - PR title validation
  - [.github/workflows/test-and-release.yml](.github/workflows/test-and-release.yml) - Testing & building

- **Configuration:**
  - [.releaserc.json](.releaserc.json) - Semantic release config
  - [.github/COMMIT_CONVENTION.md](.github/COMMIT_CONVENTION.md) - Commit guidelines
  - [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) - PR template

- **Documentation:**
  - [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guide

## Next Steps

1. **Configure PyPI Trusted Publisher** (see section 1 above)
2. **Update repository permissions** (see section 2 above)
3. **Set up branch protection** (optional but recommended)
4. **Make first release** following the "First Release" section
5. **Share** CONTRIBUTING.md with your contributors

---

Questions? Check the [CONTRIBUTING.md](CONTRIBUTING.md) or open an issue!
