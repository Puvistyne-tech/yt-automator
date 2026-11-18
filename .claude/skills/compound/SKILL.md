---
name: compound
description: Self-improving retrospective. After a bug fix, review finding or merged pull request, finds the root cause and recurring mistakes, then updates .claude/rules or .claude/agents with a concise, non-redundant guardrail. Invoke with /compound.
---

# /compound

Each unit of work should make the next one easier. Turn what just went wrong into a guardrail.

## 1. Gather

- The audit reports and failed checks from the last `/ship`.
- Review comments on the pull request: `gh pr view --comments`.
- The bug's reproduction and the fix diff, when the work was a bug fix.

## 2. Find the root cause

For each problem, answer in one sentence each:

- What happened?
- Why did the existing rules, agents, tests, and hooks let it through?
- Is it a one-off, or a class of mistake that will recur?

Discard one-offs. Keep only recurring classes.

## 3. Choose the cheapest guardrail that would have caught it

Prefer earlier and more deterministic, in this order:

1. a test or lint rule in the repository
2. a check in a hook under `.claude/hooks/`
3. a sentence in `.claude/rules/architecture.md` or `.claude/rules/no-comments.md`
4. a step in an agent's method under `.claude/agents/`
5. a step in `.claude/skills/ship/SKILL.md`

## 4. Write it

- Read the target file in full first. If an existing line already covers the case, sharpen that line instead of adding one.
- One guardrail is one imperative sentence, specific enough to verify.
- Never restate a rule in a second file. Never add history, dates, or anecdotes.
- Keep `CLAUDE.md` under 120 lines and each rule file under 80 lines. Merge or delete weaker lines to make room.

## 5. Deliver

Ship the guardrail through `/ship` as `chore(claude): <guardrail>`, skipping its step 6.
Report what was added, what it replaces, and which past failure it prevents.
