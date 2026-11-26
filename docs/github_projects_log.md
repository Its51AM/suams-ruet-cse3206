# GitHub Projects Learning Log & Guide — SUAMS

## 1. Setting Up GitHub Projects (Self-Directed Tool)

### Step-by-Step Setup
1. Open your GitHub repository → click the **Projects** tab → **New project** → select **Board** template.
2. Name the board: `SUAMS CSE 3206 Incremental Board`.
3. Configure columns: **Todo**, **In Progress**, and **Done** (optionally add **In Review** for open PRs).
4. Create **GitHub Issues** for each increment (e.g., `[Inc-1] Implement Authentication & RBAC`, `[Inc-6] Implement Observer/Factory/Adapter Notifications`), add labels (`feature`, `test`, `docs`), and link them to the Project board.
5. As you start a branch (`feature/authentication`), drag the issue to **In Progress**.
6. Link the PR with `Closes #<issue-number>` so merging automatically moves the card to **Done**.

---

## 2. Comparison: GitHub Projects vs. Trello

| Criterion | GitHub Projects | Trello |
| :--- | :--- | :--- |
| **Repository Integration** | Native linking to Issues, Commits, Branches, PRs, and GitHub Actions status. | Requires external Power-Ups or manual URL pasting. |
| **Automation** | Built-in auto-move when PRs open, close, or merge (`Closes #id`). | Basic Butler rules; code events need webhooks/integrations. |
| **Views** | Board, Table (spreadsheet), and Roadmap views from one dataset. | Primarily Kanban cards (additional views in paid tiers). |
| **Learning Curve for Non-Devs** | Slightly steeper; geared toward software teams using GitHub. | Very intuitive for general/non-technical project tracking. |
| **Best Fit for SUAMS** | Ideal because each increment maps directly to Issues, feature branches, and CI checks. | Better when collaborating with non-coding stakeholders. |

---

## 3. Evidence & Learning Log Template

Fill in actual dates, issue numbers, PR links, and real screenshots from your GitHub repository as you execute each increment:

| Date | Increment / Issue # | Action Taken | Status Transition | Evidence (Commit / PR / Screenshot Path) |
| :--- | :--- | :--- | :--- | :--- |
| *YYYY-MM-DD* | `#1 Auth & RBAC` | Created branch `feature/authentication`, ran TDD tests | `Todo -> In Progress -> Done` | *Link to PR #1 & board screenshot* |
| *YYYY-MM-DD* | `#2 Student Mgmt` | Implemented CRUD + mock tests | `Todo -> In Progress -> Done` | *Link to PR #2* |
| *YYYY-MM-DD* | `#3 Course Mgmt` | Implemented courses & enrollment | `Todo -> In Progress -> Done` | *Link to PR #3* |
| *YYYY-MM-DD* | `#4 Attendance` | Implemented daily attendance upsert | `Todo -> In Progress -> Done` | *Link to PR #4* |
| *YYYY-MM-DD* | `#5 Results` | Implemented RUET grade & GPA calculator | `Todo -> In Progress -> Done` | *Link to PR #5* |
| *YYYY-MM-DD* | `#6 Patterns & Notices` | Wired Factory, Adapter, Observer | `Todo -> In Progress -> Done` | *Link to PR #6* |
| *YYYY-MM-DD* | `#7 Selenium & Docs` | Verified E2E UI & CI workflow | `Todo -> In Progress -> Done` | *Link to PR #7 & Actions run* |
