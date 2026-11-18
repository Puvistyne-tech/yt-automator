# YouTube Automator

A local web app that connects your YouTube channels and runs configurable automations that create
and publish videos. Each automation combines a pipeline type, its settings, target channels,
languages, a schedule and a review rule. The first pipeline type is Kutty Stories: short story
videos for children.

Status: engineering foundation only. The platform, the UI and the first pipeline are being built.

## Requirements

- macOS on Apple silicon (Linux works for development and CI with fake model providers)
- [uv](https://docs.astral.sh/uv/), Node 22 with pnpm, and `just` (`uv tool install rust-just`)

## Commands

```bash
just setup
```

```bash
just check
```

`just check` runs linting, type checks and tests for the backend and the web UI. It is the same
command CI runs. See `CLAUDE.md` for the full list and for the development workflow.

## Layout

| Path | Contents |
| --- | --- |
| `backend/` | Python package `automator`: domain, application, pipelines, infrastructure, api |
| `web/` | React and TypeScript UI |
| `.claude/` | rules, subagents, skills and hooks that govern how changes are made |
| `.github/workflows/ci.yml` | the required `check` status |

## Licence

MIT. See `LICENSE`.
