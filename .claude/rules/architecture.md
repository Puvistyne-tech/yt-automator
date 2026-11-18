# Architecture

YouTube Automator is a local web app: a Python backend (`backend/src/automator`) and a React UI (`web/src`).
Dependencies flow in one direction. A layer may import only from the layers listed for it.

## Backend layers

| Layer | Holds | May import |
| --- | --- | --- |
| `shared` | clock, ids, hashing, result types | standard library only |
| `domain` | entities, value objects, rules, `ports.py` interfaces, pipeline contracts | `shared` |
| `application` | use cases, one per file | `domain`, `shared` |
| `pipelines` | content-type plugins and their stages | `domain`, `shared` |
| `infrastructure` | database, YouTube, model providers, ffmpeg, scheduler, secrets | `domain`, `shared` |
| `api` | FastAPI routers, request and response schemas | `application`, `domain`, `shared` |
| `composition` | composition root helpers: the `Ports` bundle and the use-case graph | `api.container`, `application`, `domain`, `shared` |
| `main.py` | composition root | everything |
| `doctor.py` | command-line entry: renders the doctor report built by `main.py` | `main.py`, `domain`, `shared` |

- `domain` performs no I/O and imports no framework: no FastAPI, SQLModel, httpx, subprocess, or filesystem access.
- `application` reaches the outside world only through `domain/ports.py` interfaces.
- `infrastructure` implements ports. Nothing imports `infrastructure` except `main.py`.
- A class that implements a port lives in `infrastructure`, even when it only delegates to a pure `domain` function.
- `pipelines` receive providers through ports. A pipeline never imports a concrete adapter or another pipeline.
- `api` translates HTTP to use-case calls. No business rules, no database queries, no provider calls.
- Only `main.py` constructs adapters and wires them to ports. `composition` binds ports to use cases,
  constructs no adapter, and is imported only by `main.py`. `api` never imports `composition`.
- `backend/tests/unit/test_architecture.py` enforces this table. Change both together.

## Web layers

| Layer | Holds | May import |
| --- | --- | --- |
| `shared` | UI primitives, hooks, formatting | external packages only |
| `api` | typed HTTP client and query hooks | `shared` |
| `features` | one folder per capability | `api`, `shared` |
| `pages` | route screens composing features | `features`, `api`, `shared` |
| `app` | router, layout, providers | everything |

- A feature never imports another feature. Shared needs move down into `shared`.
- Components render and delegate. Data fetching lives in `api` hooks, decisions in plain functions.
- No `fetch` call outside `web/src/api`.

## Configurability

- Every user-tunable value is a field in a settings schema, never a constant in a stage or component.
- A pipeline declares its settings as a Pydantic model. The UI renders forms from the generated JSON Schema.
- Adding a content type means adding a folder under `pipelines/`. It must not require UI or API changes.

## Module discipline

- One responsibility per module. Soft limit of 200 lines per file and 40 lines per function.
- No circular imports. No `utils.py` or `helpers.py` grab-bags: name a module after what it does.
- Secrets never enter the repository, logs, or API responses.
- Every external tool sits behind a port with a fake implementation for tests.
- `docs/spec/platform.md` is the contract. Code and spec change in the same pull request and never disagree.
