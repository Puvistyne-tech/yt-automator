# Platform specification

The contract every layer and the UI build against. Change it in the same pull request as the code.

## Concepts

| Concept | Meaning |
| --- | --- |
| Credential | One Google API project (OAuth client id and secret). Owns a daily quota budget. |
| Channel | One YouTube channel connected through a credential. Holds upload defaults. |
| Pipeline | A content-type plugin. Declares a settings schema, stages, languages and output variants. |
| Automation | A pipeline type + settings + languages + targets + schedule + review policy. |
| Target | Where one language and variant of an automation's output is published: a channel plus overrides. |
| Run | One execution of an automation: stage progress, artifacts, score, review, uploads. |
| Provider | A named implementation of a capability (llm, image, motion, tts, music) with options. |
| Secret | A named value (API key, OAuth token) stored in the keychain, never returned by the API. |

## Domain model

All ids are opaque strings from `IdGenerator`. All times are timezone-aware UTC ISO 8601 strings in JSON.
JSON uses `snake_case`.

```
Credential      id, name, client_id, daily_quota_units=10000, created_at
                secret "credential/<id>/client_secret"
Channel         id, credential_id, youtube_channel_id, title, thumbnail_url, status, defaults, connected_at
                status: connected | expired | revoked
                secret "channel/<id>/token"
ChannelDefaults privacy: private|unlisted|public = private, made_for_kids: bool = false,
                category_id: str = "22", default_language: str = "en", notify_subscribers: bool = false

PipelineDescriptor  type_id, name, description, version, settings_schema (JSON Schema object),
                    default_settings (object), ui_schema (object), stages: [StageDescriptor],
                    languages: [LanguageOption], variants: [VariantOption], capabilities: [str]
StageDescriptor     id, title, description
LanguageOption      code, name
VariantOption       id, name, aspect ("16:9" | "9:16"), description

Automation      id, name, description, pipeline_type, settings (object), languages: [code],
                targets: [Target], schedule, review_policy, enabled, created_at, updated_at,
                next_run_at (nullable, derived), last_run (nullable RunSummary, derived)
Target          id, channel_id, language, variants: [variant id], privacy (nullable = channel default),
                made_for_kids (nullable = channel default), playlist_id (nullable),
                publish_delay_minutes: int = 0
Schedule        kind: manual | interval | cron, every_hours (interval), cron (5-field expression),
                timezone (IANA, default "UTC")
ReviewPolicy    mode: always | auto_when_score_at_least, min_score: float 0..100 = 85

Run             id, automation_id, automation_name, pipeline_type, status, trigger: manual|schedule,
                languages, settings_snapshot, stages: [StageRun], artifacts: [Artifact], score (nullable),
                score_details: [ScoreItem], review (nullable), uploads: [Upload], error (nullable),
                created_at, started_at, finished_at
                status: queued | running | awaiting_review | approved | rejected | publishing |
                        published | failed | cancelled
StageRun        stage_id, title, status: pending|running|done|failed|skipped, provider, message,
                started_at, finished_at
Artifact        id, kind: video|subtitle|thumbnail|metadata|image|audio|text, stage_id, language (nullable),
                variant (nullable), filename, media_type, size_bytes, meta (object)
ScoreItem       id, title, score 0..100, weight, detail
Review          decision: approved|rejected, notes, decided_at
Upload          target_id, channel_id, language, variant, status: pending|uploading|done|failed|skipped,
                youtube_video_id, url, error, quota_units
RunSummary      id, status, score, created_at, finished_at
RunEvent        run_id, kind: status|stage|log|artifact|upload, at, payload (object)

ProviderConfig  capability, chain: [ProviderChoice]
ProviderChoice  provider_id, enabled, options (object)
ProviderDescriptor  provider_id, capability, name, description, options_schema, required_secrets: [name],
                    offline: bool, available: bool, unavailable_reason
AppSettings     timezone = "UTC", max_parallel_runs = 1, keep_runs_days = 30, data_dir (read-only)
```

### Rules

- An automation's `settings` must validate against its pipeline's settings model. Unknown pipeline type is an error.
- Every automation language must be one the pipeline offers. Every target language must be in the automation's languages. Every target variant must be one the pipeline offers. Every target channel must exist.
- An automation with schedule `interval` needs `every_hours >= 1`. With `cron` it needs a valid 5-field expression.
- A run snapshots the automation's settings and languages at creation. Editing the automation never changes a past run.
- Stage order is the pipeline's. A stage failure fails the run. A retry re-runs from a chosen stage and keeps earlier artifacts.
- After the last stage the run is scored, then becomes `awaiting_review`, or `approved` directly when the policy is `auto_when_score_at_least` and the score reaches `min_score`.
- Only an `approved` run can publish. Publishing creates one upload per target and variant. A failed upload fails only itself; the run is `published` when at least one upload is done and none is pending.
- Publishing refuses when the credential's remaining daily quota is below the cost of the upload (1600 units per video, 50 per thumbnail, 400 per caption track).
- Deleting a channel is refused while an enabled automation targets it. Deleting a credential is refused while a channel uses it. Deleting an automation keeps its runs.
- Made-for-kids on a target can only be forced on by a pipeline that declares the capability `kids_content`; such a pipeline's targets are always made for kids.

## Ports (`domain/ports.py`)

`CredentialRepository`, `ChannelRepository`, `AutomationRepository`, `RunRepository`, `ProviderConfigRepository`,
`AppSettingsRepository` (get, list, save, delete as applicable), `QuotaLedger` (used_today, record),
`SecretStore` (get, set, delete, has), `Clock` (now), `IdGenerator` (new), `PipelineRegistry` (list, get),
`ProviderCatalog` (descriptors, resolve capability chain), `YouTubeGateway` (authorization_url, exchange_code,
describe_channel, upload_video, set_thumbnail, upload_captions, add_to_playlist, list_playlists),
`ArtifactStore` (workspace for a run, save, open, delete run), `RunQueue` (enqueue, cancel),
`RunEvents` (publish, subscribe), `ScheduleCalculator` (next_run_at).

## Pipeline contract (`domain/pipeline.py`)

```
class Pipeline(Protocol):
    descriptor: PipelineDescriptor
    settings_model: type[BaseModel]
    def stages(self) -> Sequence[Stage]
    def score(self, context: StageContext) -> Sequence[ScoreItem]

class Stage(Protocol):
    descriptor: StageDescriptor
    def run(self, context: StageContext) -> StageOutcome

StageContext    run_id, settings (validated model instance), languages, workspace (Path),
                artifacts (those produced so far), providers (ProviderResolver), log(message)
StageOutcome    artifacts: [NewArtifact], provider: str, message: str
NewArtifact     kind, path (inside workspace), language, variant, media_type, meta
ProviderResolver.resolve(capability) -> the first available provider in the configured chain
```

Capability interfaces live in `domain/capabilities.py`: `TextGenerator`, `ImageGenerator`, `MotionGenerator`,
`SpeechSynthesizer`, `MusicGenerator`, `MediaToolkit`. Pipelines depend on these only.

## HTTP API

Base path `/api`. Errors are `{"error": {"code": str, "message": str, "fields": {path: message}}}` with
status 400 (validation), 404, 409 (rule conflict) or 502 (upstream). Lists return bare JSON arrays.

| Method and path | Body | Returns |
| --- | --- | --- |
| GET `/health` | | `{status, version}` |
| GET `/dashboard` | | `{automations, enabled_automations, channels, runs_awaiting_review, runs_today, recent_runs: [RunSummary + automation_name], quota: [{credential_id, name, used, limit}]}` |
| GET `/pipelines` | | `[PipelineDescriptor]` |
| GET `/pipelines/{type_id}` | | `PipelineDescriptor` |
| GET `/credentials` | | `[Credential + has_secret + quota_used_today]` |
| POST `/credentials` | `{name, client_id, client_secret, daily_quota_units?}` | Credential, 201 |
| PATCH `/credentials/{id}` | any of the above | Credential |
| DELETE `/credentials/{id}` | | 204 |
| GET `/channels` | | `[Channel]` |
| POST `/channels/connect` | `{credential_id}` | `{authorization_url}` |
| GET `/oauth/callback?code&state` | | redirects to `/channels?connected=<id>` or `?error=<code>` |
| PATCH `/channels/{id}` | `{defaults}` | Channel |
| DELETE `/channels/{id}` | | 204 |
| GET `/channels/{id}/playlists` | | `[{id, title}]` |
| GET `/automations` | | `[Automation]` |
| POST `/automations` | `AutomationInput` | Automation, 201 |
| GET `/automations/{id}` | | Automation |
| PUT `/automations/{id}` | `AutomationInput` | Automation |
| PATCH `/automations/{id}` | `{enabled}` | Automation |
| DELETE `/automations/{id}` | | 204 |
| POST `/automations/{id}/duplicate` | | Automation, 201 |
| POST `/automations/{id}/runs` | | Run, 201 |
| GET `/runs?automation_id&status&limit` | | `[Run]` newest first |
| GET `/runs/{id}` | | Run |
| POST `/runs/{id}/retry` | `{from_stage?}` | Run |
| POST `/runs/{id}/cancel` | | Run |
| POST `/runs/{id}/review` | `{decision, notes?}` | Run |
| POST `/runs/{id}/publish` | | Run |
| DELETE `/runs/{id}` | | 204 |
| GET `/runs/{id}/artifacts/{artifact_id}` | | the file, with range support |
| GET `/events` | | server-sent events, each `data:` a RunEvent |
| GET `/providers` | | `{descriptors: [ProviderDescriptor], config: [ProviderConfig]}` |
| PUT `/providers` | `[ProviderConfig]` | `[ProviderConfig]` |
| GET `/secrets` | | `[{name, title, description, is_set}]` |
| PUT `/secrets/{name}` | `{value}` | 204 |
| DELETE `/secrets/{name}` | | 204 |
| GET `/settings` | | AppSettings |
| PUT `/settings` | AppSettings without `data_dir` | AppSettings |

`AutomationInput` is Automation without `id`, timestamps and derived fields. Target `id` is optional on input.

## UI

Routes: `/` dashboard, `/automations`, `/automations/new`, `/automations/:id`, `/runs`, `/runs/:id`,
`/channels`, `/providers`, `/settings`.

- Automations list: name, pipeline, languages, targets, schedule, next run, last run status, enabled switch,
  actions (run now, edit, duplicate, delete with confirmation).
- Automation editor: sections General, Content (form generated from `settings_schema` and `ui_schema`),
  Languages (multi-select from the pipeline's languages), Targets (rows of channel, language, variants,
  privacy, playlist), Schedule, Review. Client-side validation mirrors the rules; server errors map to fields.
- Run detail: live stage timeline, logs, artifacts grouped by language and variant with video players,
  subtitles and metadata, score breakdown, approve or reject with notes, publish, retry from stage.
- Channels: credentials and their quota meters, connect flow, per-channel defaults, disconnect.
- Providers: per capability, an ordered chain with enable switches and options forms; secrets with set/clear.
- Every list has loading, empty and error states. Every destructive action asks for confirmation.
