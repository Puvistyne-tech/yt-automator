# AutoTube

A local web app that connects any number of YouTube channels and runs any number of configurable
automations against them. Each automation is a pipeline type plus settings, target channels, languages,
a schedule and a review rule. Kids story videos (`kids_story`) is the first pipeline type.

- `backend/` Python 3.12, FastAPI, SQLite. Package `autotube` under `backend/src`.
- `web/` React, Vite, TypeScript. Forms are generated from each pipeline's settings schema.
- Everything must run at zero cost on an Apple-silicon Mac, with offline fakes for tests and CI.

## Commands

Run from the repository root. `just` is installed with `uv tool install rust-just`.

| Command | Does |
| --- | --- |
| `just setup` | install backend and web dependencies |
| `just dev` | run the API and the UI with reload |
| `just fmt` | format and auto-fix (ruff, Biome) |
| `just lint` | comment scan, ruff, Biome |
| `just typecheck` | `mypy --strict`, `tsc` |
| `just test` | pytest, Vitest |
| `just test-backend <args>` | run selected backend tests |
| `just test-web <args>` | run selected web tests |
| `just check` | lint, typecheck and test: exactly what CI runs |

After a failure, rerun only the failing command or test until it passes, then `just check` once.

## Rules

These load automatically and are mandatory:

- `.claude/rules/no-comments.md`: zero comments or docstrings in Python and TypeScript.
- `.claude/rules/architecture.md`: layers, allowed imports, configurability, module limits.

`backend/tests/unit/test_architecture.py` enforces the backend layer table. Change both together.

## Roles

| Role | Model | Responsibility |
| --- | --- | --- |
| Orchestrator (main session) | Fable | plans, splits work, delegates, runs `/ship` and `/compound` |
| `implementer` | Opus | all development and fixes, one scoped task at a time, with tests |
| `architecture-guardian` | Opus | read-only review of the diff against the rules |
| `code-deduplicator` | Sonnet | read-only duplication audit of production code |
| `test-deduplicator` | Sonnet | read-only audit of tests and missing coverage |

The orchestrator does not write product code itself. It writes plans and delegates to `implementer`.

## Mandatory workflow loop

Every change, however small, goes through all six steps.

1. **Plan**: state the goal, the files and layers touched, the contracts, and the tests that prove it.
   Split into tasks that do not share files so implementers can run in parallel.
2. **Implement**: delegate each task to `implementer`. Tests first.
3. **Parallel Audit**: `code-deduplicator`, `test-deduplicator` and `architecture-guardian` on the diff.
4. **Automated Review**: fix every blocking finding, rerun checks, then one final self-review.
5. **PR & Auto-Merge**: Conventional Commit, feature branch, `gh pr create`,
   `gh pr merge --squash --auto --delete-branch`. The required `check` status gates the merge.
6. **Compound**: `/compound` turns what went wrong into one guardrail in rules, agents, hooks or tests.

`/ship` runs steps 3 to 6. Never merge by any other route.

## Branches and commits

- Never commit to or push `main`. Hooks block it.
- Branch names: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `refactor/<slug>`.
- Conventional Commits: `type(scope): summary`, imperative, under 72 characters.
- Scopes: `domain`, `application`, `infrastructure`, `pipelines`, `api`, `web`, `claude`, `ci`.
- One logical change per pull request. Keep diffs under about 600 changed lines where possible.
- Pull requests are squash-merged. Start every branch from a fresh `origin/main`, and merge `origin/main`
  into any branch that was cut before its base was merged.

## Hooks

Configured in `.claude/settings.json`, implemented as standard-library Python in `.claude/hooks/`.

- After `Edit` or `Write`: formats and lints the edited file and reports comments the edit added.
- Before `Bash`: blocks pushes and commits to `main`, force pushes, `rm -rf`, `git reset --hard`, `-X ours`/`-s ours` merges,
  and `gh pr merge` unless `/ship` has verified the current commit.
- After compaction: prints both rule files back into context.

A blocked command is a signal to use the workflow, not to find another route.

## Product principles

- **Everything is configurable.** A tunable value is a field in a settings schema with a default,
  a title and a description, so the UI can render and validate it. No constants buried in stages.
- **Plugins, not branches.** A new content type is a new folder under `pipelines/`. It must not
  require changes to `api/` or `web/`.
- **Ports for every external tool.** YouTube, model providers, ffmpeg, the clock and secrets sit
  behind interfaces in `domain/ports.py`, each with a fake used by tests.
- **Safe by default.** Uploads are private and wait for review unless an automation says otherwise.
  Kids' content is always marked made-for-kids.
- **Secrets stay local.** OAuth tokens and API keys live in the keychain, never in the repository,
  logs or API responses.

## Where things run

- Cloud sessions and CI have no GPU. They use the fake providers.
- Real models (image, video, voice, music) run only on the Mac, after `scripts/setup.sh`.
