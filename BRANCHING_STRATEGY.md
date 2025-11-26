# Branching Strategy

This project follows **GitHub Flow** - a simple, lightweight branching model suitable for continuous deployment.

## Overview

```
main (production) ← feature branches
```

- `main` is always deployable and matches production
- All work happens in feature branches created from `main`
- Changes are merged back via Pull Requests
- Deploy after merge

## Branch Naming Convention

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New functionality | `feature/job-search` |
| `fix/` | Bug fixes | `fix/scraper-timeout` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |

## Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-feature
   ```

2. **Make commits** with clear messages:
   ```bash
   git add .
   git commit -m "Add job search functionality"
   ```

3. **Push and open a PR**:
   ```bash
   git push -u origin feature/my-feature
   gh pr create --title "Add job search" --body "Description of changes"
   ```

4. **Merge after review** and delete the branch

5. **Deploy** to production:
   ```bash
   ssh tachyon "cd ~/apps/far-reach-jobs && git pull origin main && docker compose down && docker compose up -d --build"
   ```

## Why GitHub Flow?

For a small team/solo project with continuous deployment:

- **Simple**: No complex develop/release/hotfix branches
- **Clear**: Every PR is a reviewable unit of work
- **Fast**: Minimal overhead from branch to production

GitFlow adds unnecessary complexity for projects that don't need staged releases.

## Optional: Branch Protection

GitHub branch protection can be enabled on `main` to:

- Require PR reviews before merging
- Require status checks to pass (CI)
- Prevent force pushes
