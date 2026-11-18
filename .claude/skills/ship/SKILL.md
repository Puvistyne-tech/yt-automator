---
name: ship
description: End-to-end delivery pipeline. Verifies the current change, runs the three audit subagents in parallel, fixes blocking findings, self-reviews, then commits, opens a pull request and auto-merges it once checks pass. Invoke with /ship when a change is ready.
---

# /ship

Run every step in order. Stop and report if a step cannot be completed. Never skip a step.

## 0. Preconditions

- The current branch is not `main`. If it is, create `feat/<slug>`, `fix/<slug>`, or `chore/<slug>` first.
- `git status` shows only changes that belong to this task.

## 1. Verify

Run `just check`. If anything fails, fix it and rerun only the failing command until it passes.

## 2. Parallel audit

1. Write the diff where read-only agents can reach it:
   `git add -A -N && git diff origin/main > .claude/.ship-diff.patch && git diff --name-only origin/main > .claude/.ship-files.txt`
2. In a single message, spawn `code-deduplicator`, `test-deduplicator`, and `architecture-guardian`, each given the two file paths above.
   Give each the checkout path to read, and for a diff over 2,000 lines tell it to read the files directly.
3. Collect all three reports.

## 3. Fix

- Hand every `blocking` finding to the `implementer` subagent, grouped by file.
- Rerun `just check`. Rerun only the auditors that reported `RESULT: FAIL`, on a diff of the fix commits only,
  telling each what round one reported so it verifies those and checks the fixes for regressions.
- Repeat until all three report `RESULT: PASS`. After three rounds without convergence, stop and report.
- List `advisory` findings in the pull request body. Do not fix them in this change.

## 4. Self-review

Read the final diff once as a reviewer: correctness, error paths, security, secrets, unrelated changes, leftover debug output.
Fix what you find and rerun the affected check.

## 5. Deliver

1. `git add -A` then commit with a Conventional Commit message: `type(scope): summary`.
2. `git rev-parse HEAD > .claude/.ship-verified`
3. `git push -u origin <branch>`
4. `gh pr create --fill-first --base main`, with a body that states what changed, how it was verified, and the advisory findings.
5. `gh pr merge --squash --auto --delete-branch`
6. `gh pr checks --watch --fail-fast`. If a check fails, read its log, fix, and return to step 1.
   If the pull request reports a conflict, merge `origin/main` into the branch, rerun `just check`, and push.
7. Confirm the merge with `gh pr view --json state`, then `git checkout main && git pull --ff-only`.

## 6. Compound

Run `/compound` with the audit findings and any failure met along the way.
