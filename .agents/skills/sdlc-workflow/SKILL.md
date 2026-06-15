---
name: sdlc-workflow
description: "Use when Codex needs to manage software development lifecycle work in this repo: choosing or creating branches, starting issue work, preparing commits, opening pull requests, requesting or addressing review, merging, closing issues, or updating milestone tracking issues."
---

# SDLC Workflow

Use this skill to keep issue-driven GitHub work consistent and auditable.

## Operating Principles

- Start from the GitHub issue or milestone whenever possible.
- Prefer one issue per branch and one branch per pull request.
- Keep scope narrow; create follow-up issues for new work discovered along the way.
- Preserve unrelated user changes in the working tree.
- Update any relevant `tracking` issue when child issues close or change order/status.
- Do not merge or close issues unless the user asks for that workflow or has clearly delegated it.
- Always use squash merge for pull requests. Do not use merge commits or rebase merge unless the user explicitly overrides this rule for a specific PR.

## Start Issue Work

1. Read the issue and linked tracking issue or milestone.
2. Check local state with `git status --short --branch`.
3. If the work needs code or docs changes, create a branch from the intended base branch.
4. Name the branch by issue type:
   - `fix/<issue-number>-<short-slug>`
   - `feature/<issue-number>-<short-slug>`
   - `docs/<issue-number>-<short-slug>`
   - `chore/<issue-number>-<short-slug>`
5. If the issue belongs to a milestone, find any open issue in that milestone labeled `tracking` and keep it in mind for closure updates.

## Implement

1. Inspect the relevant files before editing.
2. Make the smallest coherent change that satisfies the issue.
3. Keep generated artifacts and source edits separate when practical.
4. Run validation scaled to the blast radius.

For this project, full pipeline/publication validation is:

```bash
npm run status
npm run pipeline
npm run validate
quarto render
```

## Commit

1. Review the diff before staging.
2. Stage only files that belong to the issue.
3. Use a concise imperative commit message.
4. Mention the issue number in the commit body when helpful.

## Open A Pull Request

1. Push the branch.
2. Open a draft PR unless the user asks for ready-for-review.
3. Include:
   - linked issue, using `Closes #N` only when merge should close it
   - summary of changes
   - validation commands and results
   - known limitations or follow-up work
4. Request review or trigger Codex review only when the user asks or repo practice requires it.

## Address Review

1. Read review comments and classify each as actionable, question, or out of scope.
2. Fix actionable items with the smallest change.
3. Re-run the relevant validation.
4. Push a follow-up commit.
5. Reply or summarize what changed, especially for comments not fully addressed.

## Merge And Close

Only do this when the user explicitly asks.

1. Confirm the PR is approved or the user wants to merge despite pending review.
2. Confirm required checks and validation have passed, or clearly report any skipped checks.
3. Merge with squash merge.
4. Confirm linked issues closed as expected.
5. For each closed milestone issue, update the open same-milestone issue labeled `tracking`:
   - check off the issue
   - note out-of-order completion or dependency changes
   - close the tracking issue only when its completion definition is met

## If Blocked

Report the exact blocker, what was verified, and the smallest next action. Do not invent branch, PR, merge, or review state; check GitHub or local git first.
