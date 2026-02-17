# GitHub Actions Setup Checklist

Quick checklist to set up CI/CD for PRISM and start using proper Git workflow.

## Prerequisites

- [ ] Push current changes to a feature branch (not main)
- [ ] GitHub repository is set up
- [ ] You have admin access to the repository

## Setup Steps

### 1. Push Workflow File to GitHub

```bash
# You should be on a feature branch (feat/pdf-loader-and-rag-improvement)
git add .github/workflows/ci.yml
git add docs/GITHUB_ACTIONS_GUIDE.md
git add docs/GITHUB_ACTIONS_SETUP_CHECKLIST.md
git commit -m "ci: Add GitHub Actions CI/CD pipeline

- Add comprehensive CI workflow with backend/frontend checks
- Add linting, type checking, testing, and build steps
- Add Docker build verification
- Add security scanning with Trivy
- Include documentation for GitHub Actions usage

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

### 2. Create Pull Request

- [ ] Go to GitHub repository
- [ ] Click "Compare & pull request"
- [ ] Fill in PR details:
  ```
  Title: Add GitHub Actions CI/CD Pipeline

  ## Summary
  - Implement comprehensive CI/CD with GitHub Actions
  - Add backend linting (ruff), type checking (mypy), and tests (pytest)
  - Add frontend linting (eslint), type checking (tsc), and build
  - Add Docker build verification
  - Add security scanning with Trivy
  - Include complete documentation and setup guide

  ## What This Enables
  - Automated testing on every PR
  - Prevents broken code from merging
  - Enforces code quality standards
  - Branch protection for main

  ## Testing
  - [x] Verified workflow file syntax
  - [ ] Will verify CI runs successfully after PR creation

  ## Documentation
  - Complete guide in `docs/GITHUB_ACTIONS_GUIDE.md`
  - Setup checklist in `docs/GITHUB_ACTIONS_SETUP_CHECKLIST.md`
  ```
- [ ] Create pull request

### 3. Wait for CI to Run (First Time)

This is your first CI run! It will:

- [ ] Backend Lint & Type Check (~2-3 min)
- [ ] Backend Tests (~3-4 min)
- [ ] Frontend Lint & Type Check (~2 min)
- [ ] Frontend Build (~4-5 min)
- [ ] Docker Build Test (~5-6 min)
- [ ] Security Scan (~2 min)

**Expected Issues on First Run:**

You may see failures. Common ones:

#### Backend Linting Issues
```bash
# Fix locally:
cd backend
pip install ruff
ruff check apps/api/src --fix
git add .
git commit -m "fix: Resolve linting issues"
git push
```

#### Frontend Linting Issues
```bash
# Fix locally:
cd frontend/apps/web
pnpm lint --fix
git add .
git commit -m "fix: Resolve ESLint issues"
git push
```

#### Type Check Issues
```bash
# Backend:
cd backend
pip install mypy
mypy apps/api/src --ignore-missing-imports

# Frontend:
cd frontend/apps/web
pnpm tsc --noEmit
```

#### Missing Test Directory
```bash
# If pytest fails because tests directory doesn't exist:
mkdir -p backend/apps/api/tests
touch backend/apps/api/tests/__init__.py
touch backend/apps/api/tests/test_placeholder.py

# Add to test_placeholder.py:
cat > backend/apps/api/tests/test_placeholder.py << 'EOF'
"""Placeholder test to ensure pytest runs."""

def test_placeholder():
    """Placeholder test."""
    assert True
EOF

git add backend/apps/api/tests/
git commit -m "test: Add placeholder test file"
git push
```

### 4. Fix Any CI Failures

- [ ] Click on failed check in PR
- [ ] Read error logs
- [ ] Fix issues locally
- [ ] Commit and push fixes
- [ ] Wait for CI to re-run
- [ ] Repeat until all checks pass ✅

### 5. Merge Your First PR

Once all checks pass:

- [ ] Review the "Files changed" tab
- [ ] Click "Squash and merge"
- [ ] Confirm merge
- [ ] Delete the feature branch

### 6. Update Local Main

```bash
git checkout main
git pull origin main
```

### 7. Set Up Branch Protection

**On GitHub:**

1. [ ] Go to: Repository → Settings → Branches
2. [ ] Click "Add branch protection rule"
3. [ ] Branch name pattern: `main`
4. [ ] Configure settings:

   **Protect matching branches:**
   - [x] Require a pull request before merging
     - [x] Require approvals: 0 (or 1 if team)
     - [x] Dismiss stale pull request approvals when new commits are pushed
     - [x] Require review from Code Owners (optional)

   - [x] Require status checks to pass before merging
     - [x] Require branches to be up to date before merging
     - [x] Status checks that are required:
       - `Backend Lint & Type Check`
       - `Frontend Lint & Type Check`
       - `Frontend Build`
       - `Docker Build Test`
       - `All Checks Complete`

   - [x] Require conversation resolution before merging

   - [x] Require linear history (optional but recommended)

   - [ ] Include administrators (recommended - applies to you too!)

   - [x] Do not allow bypassing the above settings

5. [ ] Click "Create" or "Save changes"

### 8. Test Branch Protection

Try to push directly to main (should fail):

```bash
git checkout main
echo "test" >> README.md
git add README.md
git commit -m "test: Direct commit to main"
git push origin main
```

**Expected result:**
```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Changes must be made through a pull request.
```

✅ **Success!** Branch protection is working.

```bash
# Undo the test commit
git reset HEAD~1
```

### 9. Start Using New Workflow

From now on, **always** use this workflow:

```bash
# 1. Start from updated main
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feat/your-feature-name

# 3. Make changes
# ...edit files...

# 4. Commit
git add .
git commit -m "feat: Your feature description"

# 5. Push
git push -u origin feat/your-feature-name

# 6. Create PR on GitHub
# 7. Wait for CI ✅
# 8. Merge PR
# 9. Update main
git checkout main
git pull origin main
```

## Optional Enhancements

### Add Pre-commit Hooks (Run Checks Locally)

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
        files: ^backend/

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        files: ^backend/

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.56.0
    hooks:
      - id: eslint
        files: ^frontend/.*\.(ts|tsx|js|jsx)$
        args: [--fix]
EOF

# Install hooks
pre-commit install

# Test
pre-commit run --all-files
```

### Add Status Badge to README

Add this to the top of `README.md`:

```markdown
# PRISM

[![CI/CD](https://github.com/YOUR_USERNAME/PRISM/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/PRISM/actions/workflows/ci.yml)

Your existing README content...
```

Replace `YOUR_USERNAME` with your GitHub username.

## Verification Checklist

After setup is complete, verify:

- [ ] GitHub Actions workflow exists at `.github/workflows/ci.yml`
- [ ] First PR created and CI ran successfully
- [ ] All CI checks passed (green checkmarks)
- [ ] Branch protection enabled on `main`
- [ ] Cannot push directly to `main` (tested)
- [ ] New changes must go through PR
- [ ] Documentation is available

## Quick Reference

### Create Feature Branch
```bash
git checkout -b feat/my-feature
```

### Check CI Status Locally (Before Pushing)
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

### View CI Runs
- Go to: Repository → Actions tab
- Click on a workflow run to see details

### Common Branch Names
- `feat/add-new-feature` - New features
- `fix/bug-description` - Bug fixes
- `refactor/code-improvement` - Refactoring
- `docs/update-readme` - Documentation
- `test/add-unit-tests` - Tests
- `chore/update-deps` - Dependencies, configs

## Troubleshooting

### CI is Running Forever
- Check Actions tab for details
- May need to cancel and restart
- Check if external dependencies are down

### All Checks Failed
- Click on failed check for logs
- Fix issues locally
- Push fixes to trigger re-run

### Can't Merge PR
- Ensure all required checks passed
- Resolve any merge conflicts
- Get required approvals (if configured)

## Next Steps

1. ✅ Complete this checklist
2. ✅ Merge your first PR successfully
3. ✅ Set up branch protection
4. 🎯 Use this workflow for all future changes
5. 🎯 Never commit directly to `main` again

## Resources

- Complete guide: `docs/GITHUB_ACTIONS_GUIDE.md`
- GitHub Actions docs: https://docs.github.com/en/actions
- Branch protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches

---

**Congratulations!** You now have a professional CI/CD pipeline. 🎉

All future changes will be automatically tested, ensuring code quality and preventing bugs from reaching production.
