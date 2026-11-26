# Git and GitHub Workflow Guide — SUAMS

> **Note:** Execute these commands locally against your own GitHub repository to create genuine commit history, Pull Requests, and reviews. Never fabricate history or screenshots.

---

## 1. Branching Strategy & Naming Convention

Keep `main` always deployable and passing CI. Develop each increment on its dedicated branch:

| Increment | Branch Name |
| :--- | :--- |
| Authentication & RBAC | `feature/authentication` |
| Student Management | `feature/student-management` |
| Course Management | `feature/course-management` |
| Attendance Management | `feature/attendance` |
| Result & Grade Management | `feature/results` |
| Notices & Notification Patterns | `feature/notifications` |
| Unit, Mock & UI Test Suite | `test/unit-tests` |
| Documentation & Diagrams | `docs/project-documentation` |

### Initial Setup Commands
```bash
git init
git branch -M main
git add .gitignore requirements.txt .env.example pytest.ini README.md
git commit -m "chore: initialize SUAMS project scaffolding and configuration"
git remote add origin https://github.com/<your-username>/suams-ruet.git
git push -u origin main
```

### Working on a Feature Branch
```bash
git checkout -b feature/authentication main
# 1. Write tests first (TDD Red)
git add tests/unit/test_auth_tdd.py
git commit -m "test(auth): add failing TDD unit tests for JWT and RBAC"
# 2. Implement module (TDD Green)
git add app/core/security.py app/models/user.py app/services/auth_service.py app/routers/auth.py
git commit -m "feat(auth): implement bcrypt hashing, JWT cookie auth, and RBAC"
git push -u origin feature/authentication
```

---

## 2. Meaningful Commit Message Convention (Conventional Commits)

Format: `<type>(<scope>): <imperative summary>`
- `feat(results): implement RUET grade calculator and weighted GPA`
- `test(notifications): add mock tests for Factory and EmailAdapter`
- `fix(students): reject duplicate roll numbers on registration`
- `docs(patterns): document Observer, Factory, and Adapter trade-offs`
- `ci: configure GitHub Actions for pytest-cov and Selenium`

---

## 3. Creating & Reviewing Pull Requests on GitHub

1. **Create a PR:**
   - Open your repository on GitHub → **Pull requests** → **New pull request**.
   - Base: `main` ← Compare: `feature/authentication`.
   - Include summary, linked GitHub Issue (`Closes #1`), and test results.
   - Wait for the **SUAMS CI Pipeline** GitHub Action check to turn green.
2. **Review a PR:**
   - Open **Files changed**, inspect logic, error handling, tests, and coverage.
   - Leave line-level comments for edge cases or code quality improvements.
   - Choose **Approve** if everything passes, or **Request changes** if revisions are needed.
3. **Revise or Reject a PR:**
   - **To revise:** Push new commits to the same feature branch (`git push`); the PR updates automatically and re-triggers CI.
   - **To reject/close:** Leave a clear rationale comment explaining why the approach was superseded or rejected, then click **Close pull request**.

---

## 4. Resolving a Merge Conflict

When two branches modify the same lines (e.g., `app/main.py` router registrations):
```bash
git checkout feature/notifications
git fetch origin
git merge origin/main
# Git marks conflict regions with <<<<<<<, =======, >>>>>>>
```
1. Open the conflicted file, keep both needed imports/routers cleanly, and remove conflict markers.
2. Run tests locally (`pytest`) to ensure nothing broke.
3. Stage and commit the resolution:
```bash
git add app/main.py
git commit -m "chore: resolve router merge conflict in app/main.py"
git push origin feature/notifications
```

---

## 5. Maintaining `README.md`

Update `README.md` whenever:
- A new module, endpoint, or environment variable is introduced.
- Setup, bootstrap, or test execution commands change.
- Coverage metrics or CI badges are updated after a milestone merge.
