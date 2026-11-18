# No comments

Applies to every Python and TypeScript file you create or modify, including tests and hook scripts.

## Rule

- Zero inline comments, block comments, TODO/FIXME notes, commented-out code, or docstrings.
- Code explains itself through precise names, small single-purpose functions, and types.
- If a line seems to need a comment, extract a well-named function or variable instead.
- Explanations for humans belong in the PR description or in `README.md`, never in source.
- User-facing API text goes in arguments (`description=`, `summary=`, `help=`), not docstrings.

## Allowed, only when a tool strictly requires it

- A shebang on the first line of an executable script.
- A suppression with a specific code: `# type: ignore[code]`, `# noqa: CODE`, `// biome-ignore lint/rule: reason`, `// @ts-expect-error`.
- `/// <reference ... />` in TypeScript declaration files.

A bare `# type: ignore`, `# noqa`, or `@ts-ignore` is a violation.

## Enforcement

- `.claude/hooks/post_edit.py` reports comment lines added by an edit.
- `just lint` runs `.claude/hooks/comment_scan.py` over all source, and CI fails on any finding.
- `architecture-guardian` flags any comment left in the diff as blocking.
