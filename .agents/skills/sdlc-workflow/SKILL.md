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
- Open pull requests as ready for review, not draft.
- Keep a human control point between pull request creation and merge. Do not merge or close issues unless the user explicitly asks for that workflow or has clearly delegated it.
- Always use squash merge for pull requests. Do not use merge commits or rebase merge unless the user explicitly overrides this rule for a specific PR.

## Command Interpretation

Treat `sdlc`, `sldc`, and `$sdlc-workflow` as requests to use this workflow. `sldc` is an accepted shorthand/typo, not a reason to ask for clarification.

Issue-number commands are issue-directed workflow requests:

```text
sdlc <issue-number>
sldc <issue-number>
sdlc implement issue <issue-number>
use sdlc to finish #<issue-number>
```

The number is not a magic value. For example, `sldc 33` means inspect and start or continue issue #33, while `sldc 22` means inspect and start or continue issue #22.

`sdlc next` and `sldc next` are selection requests, not implementation approval. For these requests, inspect open issues and relevant tracker/milestone ordering, choose the next recommended issue, explain the selection briefly, and stop for user confirmation before creating a branch, editing files, or otherwise starting implementation.

For any equivalent request, first inspect the referenced issue, determine its current status, and then choose the smallest correct continuation:

- If the issue is open and no implementation branch/PR exists, start issue work.
- If a branch exists, inspect local/remote branch state and continue from it when safe.
- If an open PR exists, inspect its status, checks, review comments, and remaining scope before changing code.
- If the issue is already closed, report the closure state and do not create new work unless the user asks to reopen or follow up.

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
npm run validate
npm run pipeline
quarto render
```

## Pre-PR Codex Review

Before opening a pull request, perform a Codex code review over the staged or intended PR diff. Use the standard review stance: prioritize bugs, behavioral regressions, broken validation, missing tests, schema drift, source-risk gaps, and documentation mismatches.

Handle findings before PR creation:

1. Fix actionable in-scope findings with the smallest change.
2. Re-run validation scaled to the fix.
3. Perform a second-pass analysis after fixes to decide whether another review is needed:
   - run another review when fixes are non-trivial, touch shared behavior, change validation, or alter generated artifacts;
   - skip another review only when fixes are mechanical or documentation-only and the second-pass analysis finds no new risk.
4. For real problems that are out of PR scope or intentionally deferred, create separate GitHub issues labeled `tech debt`. If the label does not exist, create it with a concise description before filing the first issue.
5. Mention any filed tech-debt issues in the PR body under known limitations or follow-up work.

## Commit

1. Review the diff before staging.
2. Stage only files that belong to the issue.
3. Use a concise imperative commit message.
4. Mention the issue number in the commit body when helpful.

## Open A Pull Request

1. Push the branch.
2. Confirm the pre-PR Codex review has run and either all actionable findings are fixed or out-of-scope findings have tech-debt issues.
3. Open a ready PR, not a draft PR.
4. Include:
   - linked issue, using `Closes #N` only when merge should close it
   - summary of changes
   - validation commands and results
   - known limitations or follow-up work
   - tech-debt issues filed for deferred findings, if any
5. Stop after PR creation unless the user explicitly asks to merge. This preserves the human control point before merge.

## Address Review

1. Read review comments and classify each as actionable, question, or out of scope.
2. Fix actionable items with the smallest change.
3. Re-run the relevant validation.
4. Perform a second-pass analysis to decide whether another review pass is needed before proceeding:
   - request or run another review when fixes are complex, risky, or touch areas not covered by the original review;
   - proceed without another review only when the second-pass analysis finds the fix mechanical and low risk.
5. File `tech debt` issues for valid review findings not addressed in the PR.
6. Push a follow-up commit.
7. Reply or summarize what changed, especially for comments not fully addressed.

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
