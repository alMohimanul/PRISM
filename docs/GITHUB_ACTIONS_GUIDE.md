# GitHub Actions CI/CD Guide for PRISM

## Overview

This guide explains the GitHub Actions setup for PRISM and how to use proper Git workflow instead of directly committing to `main`.

## What is GitHub Actions?

GitHub Actions is a CI/CD (Continuous Integration/Continuous Deployment) platform that automatically runs tests, linting, and builds whenever you push code or create pull requests. This ensures code quality and prevents broken code from being merged.

## CI/CD Pipeline for PRISM

Our workflow (`.github/workflows/ci.yml`) includes:

### 1. **Backend Lint & Type Check**
- **Purpose**: Ensures Python code follows best practices
- **What it does**:
  - Runs `ruff` linting (checks code style, imports, security issues)
  - Runs `mypy` type checking (catches type errors)
- **When it runs**: On every push and pull request

### 2. **Backend Tests**
- **Purpose**: Runs all unit tests to ensure functionality
- **What it does**:
  - Runs `pytest` with coverage reporting
  - Uploads coverage to Codecov
- **When it runs**: On every push and pull request

### 3. **Frontend Lint & Type Check**
- **Purpose**: Ensures TypeScript/React code quality
- **What it does**:
  - Runs `eslint` (checks code style and React best practices)
  - Runs TypeScript type checking
- **When it runs**: On every push and pull request

### 4. **Frontend Build**
- **Purpose**: Ensures the app can build successfully
- **What it does**:
  - Builds Next.js production bundle
  - Verifies no build errors
- **When it runs**: After lint/typecheck passes

### 5. **Docker Build Test**
- **Purpose**: Ensures Docker images build correctly
- **What it does**:
  - Builds backend Docker image
  - Builds frontend Docker image
  - Uses layer caching for speed
- **When it runs**: On every push and pull request

### 6. **Security Scan**
- **Purpose**: Identifies security vulnerabilities
- **What it does**:
  - Runs Trivy scanner on codebase
  - Uploads results to GitHub Security tab
- **When it runs**: On every push and pull request

### 7. **All Checks Complete**
- **Purpose**: Final status check
- **What it does**:
  - Verifies all required checks passed
  - Fails if any critical check failed
- **When it runs**: After all other jobs complete

## Proper Git Workflow

### Current Problem
You mentioned: "currently we are directly merging everything to main"

This is dangerous because:
- ❌ No code review
- ❌ No automated testing before merge
- ❌ Can break production easily
- ❌ Hard to collaborate with team
- ❌ No rollback history

### Recommended Workflow

#### Step 1: Create a Feature Branch

```bash
# Make sure you're on main and it's up to date
git checkout main
git pull origin main

# Create a new feature branch
git checkout -b feat/your-feature-name

# Examples:
git checkout -b feat/add-citation-export
git checkout -b fix/pdf-highlighting-bug
git checkout -b refactor/improve-chunking
```

**Branch Naming Convention:**
- `feat/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation changes
- `test/` - Adding tests
- `chore/` - Dependencies, configs, etc.

#### Step 2: Make Your Changes

```bash
# Make code changes
# Edit files...

# Check what changed
git status
git diff

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add PDF citation export functionality

- Implement citation export to BibTeX format
- Add export button to PDF viewer
- Include page numbers in citations

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### Step 3: Push to GitHub

```bash
# First time pushing this branch
git push -u origin feat/your-feature-name

# Subsequent pushes
git push
```

#### Step 4: Create Pull Request

1. Go to GitHub repository
2. Click "Compare & pull request" (appears after push)
3. Fill in PR details:
   ```
   Title: Add PDF citation export functionality

   Description:
   ## Summary
   - Implement BibTeX export for citations
   - Add export button to PDF viewer
   - Include page numbers in exported citations

   ## Testing
   - [x] Manually tested export with 5 different papers
   - [x] Verified BibTeX format is valid
   - [x] Checked page numbers are correct

   ## Screenshots
   [Attach screenshots if UI changes]

   Closes #123 (if related to an issue)
   ```
4. Click "Create pull request"

#### Step 5: Wait for CI Checks

GitHub Actions will automatically run all checks:

```
✅ Backend Lint & Type Check - 2m 15s
✅ Backend Tests - 3m 42s
✅ Frontend Lint & Type Check - 1m 58s
✅ Frontend Build - 4m 32s
✅ Docker Build Test - 5m 18s
✅ Security Scan - 2m 05s
✅ All Checks Complete - 1s
```

If any check fails:
1. Click on the failed check to see details
2. Fix the issue in your branch
3. Commit and push again
4. CI will re-run automatically

#### Step 6: Code Review (Optional but Recommended)

If working with a team:
- Request review from team members
- Address review comments
- Make changes if requested

#### Step 7: Merge to Main

Once all checks pass:
1. Click "Merge pull request"
2. Choose merge type:
   - **Squash and merge** (recommended) - Combines all commits into one
   - **Merge commit** - Keeps all commits
   - **Rebase and merge** - Replays commits on main
3. Delete the feature branch after merging

```bash
# After merging, update your local main
git checkout main
git pull origin main

# Delete local feature branch
git branch -d feat/your-feature-name
```

## Setting Up Branch Protection

To enforce this workflow, set up branch protection rules:

### On GitHub Web:

1. Go to: Settings → Branches → Add branch protection rule
2. Branch name pattern: `main`
3. Enable these settings:
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: 1 (if team)
     - ✅ Dismiss stale reviews when new commits are pushed
   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging
     - Select required checks:
       - `Backend Lint & Type Check`
       - `Backend Tests`
       - `Frontend Lint & Type Check`
       - `Frontend Build`
       - `Docker Build Test`
   - ✅ **Require conversation resolution before merging**
   - ✅ **Do not allow bypassing the above settings** (even for admins)
   - ⚠️ **Include administrators** (applies rules to you too)

4. Click "Create" or "Save changes"

### What This Does:

- 🚫 **Prevents direct pushes to main**
- ✅ Forces all changes through pull requests
- ✅ Ensures all CI checks pass before merge
- ✅ Requires code to be up-to-date with main
- ✅ Maintains code quality automatically

## Common Workflows

### Working on Multiple Features Simultaneously

```bash
# Feature 1
git checkout -b feat/feature-one
# Make changes, commit, push
# Create PR, but don't merge yet

# Switch to feature 2 (independent)
git checkout main
git checkout -b feat/feature-two
# Make changes, commit, push
# Create PR

# Both PRs can be reviewed in parallel
```

### Updating Branch with Latest Main

```bash
# You're on feat/your-feature
# Main has new commits since you branched

# Option 1: Rebase (cleaner history)
git fetch origin
git rebase origin/main

# Option 2: Merge (preserves history)
git fetch origin
git merge origin/main

# Push updated branch (may need force push if rebased)
git push --force-with-lease
```

### Fixing CI Failures

```bash
# CI failed, need to fix

# Make fixes
# Edit files...

# Commit and push
git add .
git commit -m "fix: Resolve linting errors"
git push

# CI will automatically re-run
```

### Handling Merge Conflicts

```bash
# GitHub shows "This branch has conflicts"

# Update your branch
git fetch origin
git merge origin/main

# Fix conflicts in your editor
# Look for <<<<<<< HEAD markers

# After fixing
git add .
git commit -m "chore: Resolve merge conflicts with main"
git push

# PR will update, CI will re-run
```

## Monitoring CI/CD

### View Workflow Runs

1. Go to "Actions" tab in GitHub
2. See all workflow runs
3. Click on a run to see details
4. Click on a job to see logs

### Understanding Check Status

- ✅ **Green checkmark** - All checks passed, safe to merge
- ❌ **Red X** - Checks failed, do not merge
- 🟡 **Yellow dot** - Checks running, wait for completion
- ⚪ **Gray circle** - Checks pending/not started

### Getting Notifications

GitHub will notify you:
- 📧 Email when checks fail
- 🔔 Notification when PR is approved
- 💬 Comments on your PR

## Best Practices

### Commit Messages

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Examples:**
```bash
git commit -m "feat: Add citation export to BibTeX"
git commit -m "fix: Resolve PDF highlighting on Firefox"
git commit -m "refactor: Improve chunking algorithm performance"
git commit -m "docs: Update installation instructions"
git commit -m "test: Add unit tests for reranker service"
```

### Keep PRs Small

- ✅ One feature per PR
- ✅ Under 400 lines changed ideally
- ❌ Don't mix multiple unrelated changes
- ❌ Don't include accidental changes

### Write Good PR Descriptions

Include:
1. **What** - What does this PR do?
2. **Why** - Why is this change needed?
3. **How** - How does it work?
4. **Testing** - How did you test it?
5. **Screenshots** - If UI changes

### Review Your Own PR First

Before requesting review:
1. Read through the "Files changed" tab
2. Check for debugging code (console.logs, etc.)
3. Verify no unintended changes
4. Add comments explaining complex parts

## Troubleshooting

### CI is Slow

**Problem:** CI takes 10+ minutes

**Solutions:**
- Use caching (already configured)
- Run checks locally before pushing:
  ```bash
  # Backend
  cd backend
  ruff check apps/api/src
  mypy apps/api/src --ignore-missing-imports
  pytest

  # Frontend
  cd frontend/apps/web
  pnpm lint
  pnpm tsc --noEmit
  pnpm build
  ```

### Check Always Fails

**Problem:** A specific check always fails

**Solutions:**
1. Run it locally to reproduce
2. Check the logs in GitHub Actions
3. Fix the underlying issue
4. Update CI config if check is incorrect

### Can't Push to Main

**Problem:** `remote: error: GH006: Protected branch update failed`

**Solution:** This is expected! Create a branch and PR instead:
```bash
git checkout -b feat/my-changes
git push -u origin feat/my-changes
```

### Merge Conflicts

**Problem:** PR shows merge conflicts

**Solution:**
```bash
git fetch origin
git merge origin/main
# Fix conflicts
git add .
git commit -m "chore: Resolve merge conflicts"
git push
```

## Local Development Workflow

### Pre-commit Checks (Optional but Recommended)

Install pre-commit hooks to run checks before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Now checks run automatically on git commit
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
```

### Running CI Locally

Use `act` to run GitHub Actions locally:

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run all workflows
act

# Run specific job
act -j backend-tests
```

## Summary

### Key Changes from Current Workflow

| Before | After |
|--------|-------|
| Direct commits to main | Feature branches → PR → Main |
| No automated testing | CI runs on every PR |
| Manual code review | Automated + manual review |
| Can break production | Protected main branch |
| No quality checks | Lint, type check, tests, build |

### Migration Steps

1. ✅ **Create `.github/workflows/ci.yml`** (already done)
2. ⏭️ **Set up branch protection** (follow guide above)
3. ⏭️ **Create first PR** to test workflow
4. ⏭️ **Document in team** (if applicable)
5. ⏭️ **Enforce going forward** (all changes via PR)

### Quick Reference

```bash
# Start new feature
git checkout main && git pull
git checkout -b feat/my-feature

# Make changes
# ...edit files...
git add .
git commit -m "feat: Add my feature"
git push -u origin feat/my-feature

# Create PR on GitHub
# Wait for CI ✅
# Merge PR
# Update local main
git checkout main && git pull
```

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)

## Next Steps

1. **Set up branch protection** on GitHub (see instructions above)
2. **Create a test PR** to verify CI works correctly
3. **Commit these new files** via a PR (not directly to main!)
4. **Start using the new workflow** for all future changes

Good luck with your CI/CD setup! 🚀
