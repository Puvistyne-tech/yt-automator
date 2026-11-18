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
| Provider | A named implementation of a capability (llm, image, motion, tts, music, media) with options. |
| Secret | A named value (API key, OAuth token) stored in the keychain, never returned by the API. |

## Domain model

All ids are opaque strings from `IdGenerator`. All times are timezone-aware UTC ISO 8601 strings in JSON.
JSON uses `snake_case`.

```
Credential      id, name, client_id, daily_quota_units=10000, created_at
                secret "credential/<id>/client_secret"
Channel         id, credential_id, youtube_channel_id, title, thumbnail_url, status, defaults, connected_at
                status: connected | expired | revoked
                (becomes expired when a YouTube call fails with invalid_grant; reconnecting sets connected)
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
                languages, settings_snapshot, review_policy, stages: [StageRun], artifacts: [Artifact],
                score (nullable),
                score_details: [ScoreItem], review (nullable), uploads: [Upload], logs: [RunLog],
                error (nullable),
                created_at, started_at, finished_at,
                intermediate_removed_at (nullable: when the cleanup removed its working files)
                status: queued | running | awaiting_review | approved | rejected | publishing |
                        published | failed | cancelled
StageRun        stage_id, title, status: pending|running|done|failed|skipped, provider, message,
                started_at, finished_at
Artifact        id, kind: video|subtitle|thumbnail|metadata|image|audio|text, stage_id, language (nullable),
                variant (nullable), filename, media_type, size_bytes, meta (object)
ScoreItem       id, title, score 0..100, weight, detail
Review          decision: approved|rejected, notes, decided_at
Upload          target_id, channel_id, language, variant, status: pending|uploading|done|failed|skipped,
                youtube_video_id, url, error, quota_units,
                privacy (nullable: private|unlisted|public), made_for_kids (nullable bool),
                publish_at (nullable: when YouTube makes a delayed public upload public)
RunLog          at, level: info|warning|error = info, stage_id (nullable: null outside a stage), message
RunSummary      id, status, score, created_at, finished_at
RunEvent        run_id, kind: status|stage|log|artifact|upload, at, payload (object)
                payload by kind: status {status, error}; stage a StageRun; artifact an Artifact;
                upload an Upload; log {level, stage_id, message}

ProviderConfig  capability, chain: [ProviderChoice]
ProviderChoice  provider_id, enabled, options (object)
ProviderDescriptor  provider_id, capability, name, description, options_schema, required_secrets: [name],
                    offline: bool, available: bool, unavailable_reason
AppSettings     timezone = "UTC", max_parallel_runs = 1 (>= 1), keep_runs_days = 30 (>= 0),
                keep_intermediate_days = 0 (>= 0), auto_cleanup_enabled = false,
                cleanup_interval_hours = 24 (>= 0, whole hours),
                caption_track_name = "", max_run_log_entries = 2000 (>= 1),
                log_level: debug | info | warning | error | critical = info,
                doctor_min_free_gb = 10 (>= 0),
                data_dir (read-only), locked: {field: reason} (read-only),
                restart_required: [field] (read-only, ["log_level"])
StorageReport   data_dir, data_dir_bytes, free_bytes (nullable), disk_bytes (nullable), final_bytes,
                intermediate_bytes, orphan_bytes, other_bytes, automations: [AutomationUsage]
AutomationUsage automation_id, automation_name, runs, final_bytes, intermediate_bytes
CleanupReport   dry_run, keep_runs_days, keep_intermediate_days, items: [CleanupItem], total_bytes
CleanupItem     run_id, action: delete_run | remove_intermediate | remove_orphan,
                automation_id (nullable), automation_name, status (nullable), finished_at (nullable), bytes

DoctorReport    can_start: bool, checks: [HealthCheck], capabilities: [HealthCheck],
                providers: [ProviderHealth], missing_secrets: [SecretDefinition]
HealthCheck     name, status: ok | warning | error, detail
ProviderHealth  provider_id, capability, name, available, reason
SystemFacts     python_version, data_dir, data_dir_writable, free_bytes (nullable), ffmpeg_version,
                ffprobe_version ("" when missing), database_path, database_revision (nullable),
                database_head (nullable), database_revision_known, database_error, web_dist_dir, ui_built
DoctorPolicy    min_python = (3, 12), min_free_gb = 10 (app setting `doctor_min_free_gb`)
```

### Rules

- An automation's `settings` must validate against its pipeline's settings model. Unknown pipeline type is an error.
- A settings choice field with human titles is published in `settings_schema` as `oneOf: [{const, title}]`
  (with `type: "string"`) instead of a bare `enum`; the form shows each `title` and stores the `const`. The kids
  story pipeline titles every choice field this way through `titled_choices`.
- `ui_schema` is a react-jsonschema-form uiSchema restricted to these keys, and `domain/ui_schema.py`
  (`ui_schema_problems`) checks a pipeline's `ui_schema` against its `settings_schema`:
  - `ui:sections` (root only, optional): a list of `{title: string, fields: [string]}`. Each field is a
    top-level settings property, and when sections are given every top-level property is in exactly one
    section. The form shows the sections in list order, each under its title; without sections the form is one
    ungrouped list.
  - Any other key names a settings property and holds the hints for it; `items` holds the hints for the
    items of an array property. Nesting follows the settings schema, resolving local `$ref`s (`#/...`) and,
    for an optional property written as `anyOf`/`oneOf`, its first non-null branch (`domain/json_schema.py`).
  - `ui:widget`: one of `textarea`, `select`, `radio`, `checkboxes`, `range`, `color` (`UI_WIDGETS`; this line is
    the source both test suites read).
  - `ui:order`: a list of property names of that object. It either names every property or ends with `"*"`
    for the rest; leaving a property out without `"*"` is a problem.
  - `ui:options`: an object; the form honours `rows` on `textarea` and `step` on `range`. A `step` that is not a
    finite number above zero is ignored and the schema's own step is used.
  - No other `ui:` key is allowed. Help text comes from each field's `description` in the settings schema.
    The web mock pipeline uses this same format.
- `PipelineDescriptor` rejects a `ui_schema` with any problem, so a broken plugin fails when it is loaded.
- The kids story pipeline (`kids_story`, shown as "Kids story videos") carries no channel identity in its
  defaults: the series name defaults to "Story Time", the brand mark text is empty (no mark is drawn), and
  `{series}` is filled in with the automation's series name in the intro line, outro line, titles,
  descriptions and playlist title; the intro and outro lines take the same placeholders as the description,
  and unknown placeholders stay as written. The series name must not be blank in any language. When no bundled story
  fits the automation's cast ids and languages, the story stage fails naming both what the automation has
  and what the bundled stories need.
- Every automation language must be one the pipeline offers. Every target language must be in the automation's languages. Every target variant must be one the pipeline offers. Every target channel must exist.
- An automation with schedule `interval` needs `every_hours >= 1`. With `cron` it needs a valid 5-field expression.
- A run snapshots the automation's settings, languages and review policy at creation. Editing or deleting the automation never changes a past or queued run.
- Stage order is the pipeline's. A stage failure fails the run. A retry re-runs from a chosen stage and keeps earlier artifacts.
- Retry is allowed from `failed`, `cancelled`, `awaiting_review`, `approved` and `rejected`. It re-queues the run and clears its score, score details, review and uploads.
  Once the cleanup removed a run's working files (`intermediate_removed_at` set), a retry without a stage
  starts from the first stage, a retry from any later stage is refused with 409 `intermediate_files_removed`,
  and a retry clears `intermediate_removed_at`.
- Cancel is allowed from `queued`, `running`, `awaiting_review` and `approved`. A stage that fails after the run was cancelled is recorded as failed, but the run stays `cancelled` without an error.
- A worker records a stage result only while the stored run is `running` or `cancelled`, onto the stored run.
  If the run was retried meanwhile, the result is dropped and its unreferenced files are discarded; if the run
  was deleted, its whole folder is removed. Every run change (status moves, stage results, uploads, logs)
  is applied to the stored run through `RunRepository.update`, so concurrent cancel and retry are never lost.
  A retry that arrives while the old worker is still busy runs once that worker returns.
- Every `context.log(message, level)` call is stored on the run as a RunLog and published as a `log` event.
  A run keeps only its newest `max_run_log_entries` entries (app setting, default 2000, read at every
  log call); older entries are dropped. Every entry is still published as an event.
- Deleting a `queued`, `running` or `publishing` run is refused; cancel it first.
- After the last stage the run is scored, then becomes `awaiting_review`, or `approved` directly when the policy is `auto_when_score_at_least` and the score reaches `min_score`.
- Only an `approved` run can publish. Publishing creates one upload per target and variant. A target whose language is not in the run, whose channel no longer exists, or that has no matching video yields a `skipped` upload with the reason in `error`. A failed upload fails only itself; the run is `published` when at least one upload is done and none is pending.
- Every upload records the effective `privacy` and `made_for_kids` it was planned with (target value, else the
  channel default; kids pipelines always force made-for-kids), skipped uploads included. Uploads stored before
  these fields existed report them as null.
- When every upload fails the run returns to `approved` with the error "no upload succeeded", so it can be published again.
- On startup, interrupted runs are recovered through the normal transitions, each emitting a `status` event:
  a `running` run becomes `failed` ("interrupted: the app stopped while the run was running") and its running
  stage `failed`; a `publishing` run has every `pending` or `uploading` upload marked `failed` with
  "interrupted, check YouTube before publishing again", then becomes `published` if any upload is done, else
  `approved` with "no upload succeeded". `queued` runs are queued again, oldest first.
- A thumbnail, caption or playlist failure leaves the upload `done` and records the problem in its `error`.
- Upload details come from the run's best `metadata` artifact for the language and variant: `title`, `description`,
  `tags`, and optionally `category_id`, `default_language`, `hashtags` and `playlist_title`. A metadata `category_id`
  wins over the channel default; `default_language` (sent as `defaultLanguage` and `defaultAudioLanguage`) must look
  like a language code (`^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`) and otherwise falls back to the target language.
  Hashtags must be one token matching `#\S+`; others are ignored. A hashtag is already present when a whitespace
  token of the description equals it, compared with casefold. Missing ones are appended after a blank line, one by
  one, deduplicated with casefold, only while the description stays within 5000 UTF-8 bytes and holds at most 60
  hashtags in total. The playlist is always the target's `playlist_id`;
  `playlist_title` is informational and no playlist is ever created.
- `publish_delay_minutes` applies only when the effective privacy is `public`: the video is uploaded private with `publish_at` set to now plus the delay, and YouTube makes it public then.
- Publishing refuses when the credential's remaining daily quota is below the cost of the upload (1600 units per video, 50 per thumbnail, 400 per caption track, 50 per playlist insertion).
- The quota day resets at midnight Pacific time (`America/Los_Angeles`), as YouTube's does.
- Duplicating an automation creates a disabled copy named with the suffix " (copy)" and new target ids.
- A scheduled automation's next run is computed from the later of its last scheduled run and its `updated_at`. Manual runs do not move the schedule.
- Deleting a channel is refused while an enabled automation targets it. Deleting a credential is refused while a channel uses it. Deleting an automation keeps its runs.
- Saving provider configs (PUT `/providers`) rejects an unknown provider, a provider listed under the
  wrong capability or twice, a capability configured twice, and options that do not validate against the
  provider's options schema. Options are checked for every entry, enabled or not. Errors are keyed by
  position in the request: `<config index>.capability`, `<config index>.chain.<position>.provider_id`
  or `<config index>.chain.<position>.options.<field>` (for example `0.chain.1.options.topic_words`).
- Descriptor availability (`available`, `unavailable_reason`) is evaluated with each provider's
  default options, not the saved ones, so a provider that needs a custom path or URL may show as
  unavailable while the resolver can still use it.
- The doctor turns `SystemFacts` into checks, in this order: `python`, `data_dir`, `disk_space`,
  `ffmpeg`, `ffprobe`, `database`, `web_ui`, then `secrets` when the secret store cannot be read.
  Only three conditions are errors: Python below `min_python`, a data directory that cannot be created
  or written, and a database that cannot be read or whose revision is unknown to this app (newer).
  Low disk space, a missing ffmpeg or ffprobe, a missing UI build and unreadable secrets are warnings.
  A database that does not exist yet, or is behind the newest migration, is ok: startup migrates it.
- The doctor reports one capability check per capability: ok with the available providers in
  registry order, or a warning listing every provider's reason (offline fallbacks exist, so a
  capability without a provider never stops the app). `can_start` is false only when a check is an error.
- `python -m automator.doctor` (`just doctor`) prints the report and exits 1 when `can_start` is false
  or an `AUTOMATOR_*` setting is invalid or the system refuses access (an OS error), else 0. It
  creates no file or folder: it does not migrate or create the database, and the file secret store
  creates its key only on the first write. The one change it may make is tightening an existing
  `secrets.key` to mode 0600 when it reads secrets with the file store.
  `python -m automator.doctor --print-defaults` prints `KEY=value` lines (`DATA_DIR`, `APP_HOST`,
  `APP_PORT`, `REDIRECT_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_URL`, `ACE_STEP_DIR`, `MUSIC_DIR`) that
  `scripts/setup.sh` reads once the backend venv exists; before that it uses the same defaults.
- The OAuth redirect URI is `<redirect base>/api/oauth/callback`. The redirect base is the runtime
  setting `redirect_base_url` when set, otherwise `http://<host>:<port>` with `127.0.0.1` in place
  of a wildcard host (`0.0.0.0`, `::`), so it follows `AUTOMATOR_PORT` in both start modes.
- The file secret store creates its key with an exclusive create (mode 0600); a writer that finds
  the key already created uses it, and a store opened before the key existed reloads it from disk.
- A keychain that cannot be used (locked, or access denied) raises the same 409 `secrets_unreadable`
  as an unreadable secrets file; the message names the keychain error type, never a value.
- App settings come from three places, strongest first: an `AUTOMATOR_*` environment variable that is set
  (`AUTOMATOR_YOUTUBE_CAPTION_TRACK_NAME`, `AUTOMATOR_MAX_RUN_LOG_ENTRIES`, `AUTOMATOR_LOG_LEVEL`,
  `AUTOMATOR_DOCTOR_MIN_FREE_GB`, `AUTOMATOR_CLEANUP_INTERVAL_HOURS`), the stored value, the default.
  A field set by the environment is listed in `locked` with the reason naming the variable. `PUT /settings`
  changes only the fields it sends; a field left out keeps its current value. Saving a locked
  field with a value other than the environment's is a 400 naming the field; saving it unchanged keeps the
  stored value underneath, which applies again once the variable is unset. Settings stored before a field
  existed load with that field's default, and unknown stored keys (such as an old `data_dir`) are ignored.
- Every app setting applies without a restart except the fields in `restart_required`: `log_level` sets the
  `automator` loggers when the app starts. The caption track name is read at each caption upload, the run
  log cap at each log call, the doctor threshold at each doctor report, the cleanup interval at each
  scheduler tick and `max_parallel_runs` at each worker poll. Tuning internals (tick and poll intervals,
  queue sizes, chunk sizes, database timeouts) stay environment-only. Secrets are never app settings.
- Retention. Final outputs are artifacts of kind `video`, `thumbnail`, `subtitle` or `metadata` that have a
  language; every other artifact and the run's workspace are working files. A run's age counts from
  `finished_at`, or `created_at` when it has none.
  - The cleanup never touches a run that is `queued`, `running`, `awaiting_review`, `approved` or
    `publishing`, nor a run with a `pending` or `uploading` upload, nor one with an upload whose
    `publish_at` is still in the future.
  - Uploads stored before `publish_at` existed do not say whether they were scheduled. A `done` upload
    without `publish_at` whose privacy is `public` or unknown holds its run until `finished_at` plus its
    target's current `publish_delay_minutes`; when the target no longer exists the delay cannot be known
    and the run is kept until it is deleted by hand. Private and unlisted uploads never hold a run.
  - Any other run that is at least `keep_runs_days` days old is deleted together with its folder.
  - Any other run that is at least `keep_intermediate_days` days old (and younger than `keep_runs_days`)
    loses its working files: the run, its logs and its final outputs stay, its other artifacts leave
    `artifacts`, `intermediate_removed_at` is set once, and a log entry says how much was freed.
  - A folder under `runs/` with no run is a stray folder and is removed. Only real folders directly under
    `runs/` with an opaque id as their name count: a symbolic link is never a run folder, an `artifacts`
    link inside a run is not followed, and a link inside a run folder is removed without following it, so
    nothing outside `runs/` is measured or removed.
  - A run folder that is still there after its removal is a failure, not bytes freed.
  - 0 days keeps runs, or working files, forever.
  - Each removal re-checks the stored run in the same transaction as its database change, so a run that was
    retried, reviewed or published since the plan is left alone. Working files are removed only after the
    run is read again and is still pruned and finished, so a run retried in between keeps its files.
  - Database first, then disk: a deleted run's row goes before its folder, and pruned artifacts leave the
    row before their files. A crash in between leaves only files that the next cleanup finds (a stray
    folder, or working files of a pruned run) and removes, so there is never a row pointing at missing
    files. Folders are listed before rows, so a folder of a run created during the cleanup is never stray.
  - Running the cleanup twice removes nothing the second time. Every removal is logged with its size; a
    removal that fails is logged and skipped, and the rest continue.
  - The automatic cleanup is off until `auto_cleanup_enabled` is switched on, so an upgrade never deletes a
    run on its own. While it is on, the scheduler runs the cleanup on its next tick and then every
    `cleanup_interval_hours`; 0 also keeps it off. `POST /storage/cleanup` runs it at once; `GET /storage/cleanup` is a dry run that
    reports the same items and sizes and removes nothing.
- Storage. `GET /storage` measures the data folder on disk: its total size, final outputs and working files
  per automation (runs grouped by `automation_id`, largest first), stray folders, everything else
  (`other_bytes`: the database, secrets and other files), and the disk's size and free space, the same
  free space the doctor's `disk_space` check reads. Sizes are unknown (null) when the disk cannot be read.
- Made-for-kids on a target can only be forced on by a pipeline that declares the capability `kids_content`; such a pipeline's targets are always made for kids.

## Ports (`domain/ports.py`)

`CredentialRepository`, `AutomationRepository` (get, list, save, delete),
`RunRepository` (get, list, save, delete, update(run_id, change) -> the saved run, or None when the run is
missing or `change` returns None; the read and the write happen in one transaction;
delete_if(run_id, check) -> the deleted run, or None when it is missing or `check` refuses it, in one transaction),
`ChannelRepository` (get, find_by_youtube_id, list, save, delete), `ProviderConfigRepository` (list, save_all),
`AppSettingsRepository` (get, save), `QuotaLedger` (used_today(credential_id, day), record(credential_id, units, day)),
`SecretStore` (get, set, delete, has), `Clock` (now), `IdGenerator` (new), `PipelineRegistry` (list, get),
`ProviderCatalog` (descriptors, secrets, option_errors(configs) -> {path: message},
resolver(configs) -> ProviderResolver), `YouTubeGateway` (authorization_url,
exchange_code, describe_channel, upload_video, set_thumbnail, upload_captions, add_to_playlist, list_playlists),
`ArtifactStore` (workspace for a run, save, open, discard one artifact, delete run),
`RunFileStore` (run_ids on disk, usage(run_id, final_ids) -> FileUsage, remove_intermediate(run_id, final_ids)
-> bytes freed, delete_run(run_id) -> bytes freed, disk() -> DiskSpace; every removal is idempotent),
`RunQueue` (enqueue, cancel),
`RunEvents` (publish, subscribe), `ScheduleCalculator` (next_run_at),
`SystemInspector` (facts() -> SystemFacts: Python, data directory, free space, ffmpeg and ffprobe
versions, migration state and UI build, read without changing anything).

A YouTube failure whose code is `youtube_invalid_grant` means the channel's authorization expired.

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
                artifacts (those produced so far), providers (ProviderResolver),
                log(message, level=info) tagged with the current stage
StageOutcome    artifacts: [NewArtifact], provider: str, message: str
NewArtifact     kind, path (inside workspace), language, variant, media_type, meta
ProviderResolver.resolve(capability) -> a provider for the capability (see Provider resolution)
```

`pipelines/registry.py` is the index of installed plugins: `installed_pipelines() -> tuple[Pipeline, ...]`.
`infrastructure/pipelines/static_registry.py` holds `StaticPipelineRegistry(pipelines)`, the `PipelineRegistry` adapter
that the composition root builds from that index. It refuses two pipelines with the same `type_id`.

### Provider resolution

- The chain is the saved `ProviderConfig` for the capability. With no config, or a config whose chain
  is empty, the chain is every provider of the capability in registry order: hosted or heavy providers
  first and, where the capability has one, the always-available offline provider last.
- An entry is skipped when it is unknown, offers another capability, is disabled, has options that no
  longer validate, or reports itself unavailable. The resolver records the reason for every skipped
  entry. When no entry remains, `resolve` raises a 409 rule conflict `provider_unavailable` whose
  message lists every reason.
- `resolve` returns a failover proxy over the remaining entries in order. Each call tries them in turn
  and moves to the next only on an upstream failure (502 class). A provider's own file errors and
  output that fails validation count as upstream failures; any other error propagates at once. When
  every entry fails, the call raises an upstream failure listing each provider's message.
- The proxy's `provider_id` is the first remaining entry before any call, and afterwards the provider
  that served the most recent successful call; a stage reads it after the call to report who served it.

Capability interfaces live in `domain/capabilities.py`. There are six capabilities; pipelines depend on these only.

```
llm    TextGenerator.generate(TextRequest) -> str
image  ImageGenerator.generate(ImageRequest, output) -> Path
motion MotionGenerator.animate(MotionRequest, output) -> Path
tts    SpeechSynthesizer.synthesize(SpeechRequest, output) -> Speech
       Speech: path, duration_seconds, words: [WordTiming word, start_seconds, end_seconds],
               timing_source: synthesizer | alignment | estimate
music  MusicGenerator.compose(MusicRequest, output) -> Path
media  MediaToolkit.duration_seconds(media), compose_video(VideoComposition, output) -> Path,
       extract_frame(video, at_seconds, output) -> Path, loudness_lufs(media)
```

- `VideoComposition` and `MotionRequest` width and height are rounded down to the nearest even number
  (minimum 2), as H.264 with 4:2:0 chroma needs even sizes.
- Ducking lowers the music only while narration plays; the music continues at its set volume after
  the last narration clip.
- `extract_frame` fails with an upstream failure when no frame was written, for example past the end.
- Speech synthesizers refuse blank text with an upstream failure.
- `SubtitleStyle`: burn_in, font_family, font_file (nullable), font_size, primary, outline and highlight
  colours, margin_bottom, margin_sides, wrap_lines (default false).
- Burned-in subtitles (`subtitles` set and `SubtitleStyle.burn_in`): an SRT file is converted to an ASS
  document whose canvas is the frame size, so `font_size`, `margin_bottom` and `margin_sides` are frame
  pixels. Each SRT line is drawn as one line: the renderer does not re-wrap unless `wrap_lines` is true,
  so the producer wraps to fit. An `.ass` file is drawn as authored. Text is shaped with complex
  shaping (needed for Tamil and other Indic scripts). When `font_file` is set its folder is the font
  folder, otherwise the provider's configured fonts folder, otherwise the system fonts.
- `domain/srt.py` parses SRT into entries (start, end, lines); producers and the media toolkit share it.
- The kids story pipeline wraps each cue line to the measured frame width and splits a cue that needs more than
  `max_lines` lines into consecutive screens, each shown for at least `min_cue_seconds`, using free time
  before the next cue. Text is never dropped: when there is no time to show the parts, they join into
  one screen that may exceed `max_lines`, and sentences that start in the last `min_cue_seconds` of a
  narration join into one cue. A font whose name is unsafe, or none loading, means the configured
  fallback name with the letter width estimate; a script Pillow cannot shape keeps the font file for
  drawing and is measured by the estimate.

## HTTP API

Base path `/api`. Errors are `{"error": {"code": str, "message": str, "fields": {path: message}}}` with
status 400 (validation), 404 (`not_found` or `<entity>_not_found`), 405 (`method_not_allowed`), 409 (rule
conflict) or 502 (upstream). Any other failure is 500 with code `internal_error` and the message
"Unexpected server error"; the exception text is never returned. Lists return bare JSON arrays.
The secrets file being unreadable (missing key or corrupt file) is 409 `secrets_unreadable`, naming the
secrets and key files to remove and telling the user to reconnect their channels. The next write after
removal creates a new key. A 500 carries an `X-Request-Id` header; the log names only the error type and id.

| Method and path | Body | Returns |
| --- | --- | --- |
| GET `/health` | | `{status, version}` |
| GET `/doctor` | | DoctorReport |
| GET `/dashboard` | | `{automations, enabled_automations, channels, runs_awaiting_review, runs_today, recent_runs: [RunSummary + automation_name], quota: [{credential_id, name, used, limit}]}` |
| GET `/pipelines` | | `[PipelineDescriptor]` |
| GET `/pipelines/{type_id}` | | `PipelineDescriptor` |
| GET `/credentials` | | `[Credential + has_secret + quota_used_today]` |
| POST `/credentials` | `{name, client_id, client_secret, daily_quota_units?}` | Credential + has_secret + quota_used_today, 201 |
| PATCH `/credentials/{id}` | any of the above | Credential + has_secret + quota_used_today |
| DELETE `/credentials/{id}` | | 204 |
| GET `/channels` | | `[Channel]` |
| POST `/channels/connect` | `{credential_id}` | `{authorization_url}` |
| GET `/oauth/callback?code&state` | | redirects to `/channels?connected=<id>` or `?error=<code>` (`missing_code`, `validation_failed`, `youtube_scope_denied`, other upstream codes) |
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
| GET `/runs/{id}/artifacts/{artifact_id}` | | the file, with range support; 416 for an unsatisfiable range, 404 `artifact_file_not_found` when the file is gone |
| GET `/events` | | server-sent events: first `: connected`, then each `data:` a RunEvent, with `: heartbeat` comments |
| GET `/providers` | | `{descriptors: [ProviderDescriptor], config: [ProviderConfig]}` |
| PUT `/providers` | `[ProviderConfig]` | `[ProviderConfig]`, 400 with field errors (see Rules) |
| GET `/secrets` | | `[{name, title, description, is_set}]` |
| PUT `/secrets/{name}` | `{value}` | 204 |
| DELETE `/secrets/{name}` | | 204 |
| GET `/settings` | | AppSettings |
| PUT `/settings` | any AppSettings fields; fields left out keep their value; `data_dir`, `locked` and `restart_required` are ignored | AppSettings, 400 with field errors |
| GET `/storage` | | StorageReport |
| GET `/storage/cleanup` | | CleanupReport with `dry_run: true`; removes nothing |
| POST `/storage/cleanup` | | CleanupReport with `dry_run: false` and what was removed |

`AutomationInput` is Automation without `id`, timestamps and derived fields. Target `id` is optional on input.

The built UI is served at `/`. A path without a file extension that matches no file returns `index.html`;
a missing path with an extension (such as `/assets/missing.js`) and any `/api` path return the 404 envelope.

## UI

Routes: `/` dashboard, `/automations`, `/automations/new`, `/automations/:id`, `/runs`, `/runs/:id`,
`/channels`, `/providers`, `/settings`.

- Automations list: name, pipeline, languages, targets, schedule, next run, last run status, enabled switch,
  actions (run now, edit, duplicate, delete with confirmation).
- Automation editor: sections General, Content (form generated from `settings_schema` and `ui_schema`),
  Languages (multi-select from the pipeline's languages), Targets (rows of channel, language, variants,
  privacy, playlist), Schedule, Review. Client-side validation mirrors the rules; server errors map to fields.
  A saved automation without unsaved changes offers Run now; with unsaved changes it is disabled with the reason.
  A "Run queued" toast (list or editor) links to the new run; a toast with an action stays until it is
  used or dismissed, other toasts close after five seconds. An unknown automation id shows a not-found
  state with a link back to Automations.
- Run detail: live stage timeline, logs, score breakdown, approve or reject with notes, publish, retry from
  stage. A `status` event refetches the open run so score, score details and timestamps update live.
  Artifacts list final outputs first (kinds `video`, `thumbnail`, `subtitle`, `metadata` with a language),
  grouped by language and variant with video players, subtitles and metadata; every other artifact is an
  intermediate file, collapsed per stage in the run's stage order. The uploads table shows each upload's
  privacy and made-for-kids flag. Cancel is offered for the statuses the Rules allow. When the run's
  automation was deleted, the header says so instead of linking to it.
- Settings: three groups. General (timezone, parallel runs, caption track name), Storage and cleanup (the
  storage card with disk use per automation, final outputs versus working files and free space; keep runs,
  keep working files, the "Clean up automatically" switch (off by default) with its interval; "Clean up
  now", which works whether or not the switch is on), Logging and diagnostics (log entries per run, log
  level, free disk space warning, data folder). Every field has help text; a field in `restart_required`
  says "Applies after restart"; a locked field is read-only and shows its reason. Client-side checks mirror
  the schema and server field errors show on their fields. "Clean up now" opens a confirmation listing the
  dry run (each run, what happens to it, its size, and the total); confirming runs the cleanup and a toast
  reports what was freed; cancelling removes nothing.
- Channels: credentials and their quota meters, connect flow, per-channel defaults, disconnect.
- Providers: per capability, an ordered chain with enable switches and options forms; secrets with set/clear.
- Every list has loading, empty and error states. Every destructive action asks for confirmation.
