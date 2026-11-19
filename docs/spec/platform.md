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
PipelineTemplate    id, type_id, engine, name (non-empty; see the template rules), description,
                    audience: kids | general, status: draft | ready = draft,
                    origin: builtin | blank | duplicate | suggested, revision: int >= 1 = 1,
                    definition (object described by the engine's definition model), created_at, updated_at
TemplateSummary     PipelineTemplate + builtin: bool + automations_using: int (automations whose
                    pipeline_type is the template's type_id)
TemplateInput       engine, name, description = "", audience, status = draft, origin = blank,
                    definition (object) = {}; no other field is accepted
EngineSummary       engine_id, name, definition_schema (JSON Schema of the definition model),
                    definition_ui_schema (object), blank: {kids: object, general: object}

Automation      id, name, description, pipeline_type, settings (object), languages: [code],
                targets: [Target], schedule, review_policy, retry_policy, enabled, created_at,
                updated_at, next_run_at (nullable, derived), last_run (nullable RunSummary, derived)
Target          id, channel_id, language, variants: [variant id], privacy (nullable = channel default),
                made_for_kids (nullable = channel default), playlist_id (nullable),
                publish_delay_minutes: int >= 0 = 0, publish_time_of_day ("HH:MM" 24-hour, nullable),
                publish_timezone (IANA, default "UTC")
Schedule        kind: manual | interval | cron, every_hours (interval), cron (5-field expression),
                timezone (IANA, default "UTC"), skip_if_unfinished: bool = true,
                max_runs_per_day (nullable int >= 1 = no cap), active_from, active_until
                ("HH:MM" 24-hour, nullable, both or neither)
ReviewPolicy    mode: always | auto_when_score_at_least, min_score: float 0..100 = 85,
                reject_below (nullable float 0..100 = never), auto_publish: bool = false
RetryPolicy     auto_retry_count: int 0..10 = 0, retry_delay_minutes: int 0..1440 = 10

Run             id, automation_id, automation_name, pipeline_type, status, trigger: manual|schedule,
                languages, settings_snapshot, review_policy, retry_policy, auto_retries: int = 0,
                retry_at (nullable), skipped_start_at (nullable), stages: [StageRun],
                artifacts: [Artifact], score (nullable),
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
                publish_at (nullable: when YouTube makes a scheduled video public)
RunLog          at, level: info|warning|error = info, stage_id (nullable: null outside a stage), message
AutomationDocument  app = "AutoTube", format_version: int >= 1 (current 1), exported_at (nullable),
                    automation: Automation's name, description, pipeline_type, settings, languages,
                    schedule, review_policy, retry_policy and targets (Target without id),
                    channels: [ExportedChannel] (the target channels, each once)
ExportedChannel     id, youtube_channel_id = "", title = ""
ImportPreview       automation: AutomationInput (what the import would create), unknown_channels: [ExportedChannel]
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
  story pipeline titles every choice field this way through `titled_choices`, or `card_choices` when the entries
  also carry card keys (see `cards` below).
- A choice hint may also sit on a free string field, so the backend keeps any stored value. The form's
  select then shows a stored string that no option offers as an extra option labelled with the value itself
  (`unlistedValue` in `web/src/shared/schema-form/choices.ts`), so it is never shown as a different choice.
- `ui_schema` is a react-jsonschema-form uiSchema restricted to these keys, and `domain/ui_schema.py`
  (`ui_schema_problems`) checks a pipeline's `ui_schema` against its `settings_schema`:
  - `ui:sections` (root only, optional): a list of `{title: string, fields: [string]}`. Each field is a
    top-level settings property, and when sections are given every top-level property is in exactly one
    section. The form shows the sections in list order, each under its title; without sections the form is one
    ungrouped list.
  - `ui:basic` (root only, optional, `domain/ui_basic.py`): a list of dotted settings paths (`story.tone`,
    `look.visual_style`) that the editor's Simple view shows. Each path must resolve to a settings property
    through nested objects (with the same `$ref` and `anyOf`/`oneOf` resolution as the hints below, never into
    array `items`) and appear once; a non-list, an empty list, a non-string entry, an unknown path and a repeated
    path are problems. A listed object shows all of its children. The key is generic: the web code knows no pipeline's
    field names. The kids story pipeline lists twelve paths: series name, visual style, theme mode and themes,
    tone, target length, narrator voice, music on or off and its mood, subtitles on or off, the Short on or off,
    and the episode resolution.
  - `ui:hidden` (root only, optional, `domain/ui_hidden.py`): a list of dotted settings paths that the editor
    never shows, so a pipeline type can hide settings that do not apply to it. Entries follow the `ui:basic`
    rules (shared in `domain/ui_paths.py`), except that an empty list is valid. It is also a problem when a
    path is in both `ui:basic` and `ui:hidden`, when a `ui:basic` path lies under a hidden path, when every
    setting under a `ui:basic` path is hidden (it would show nothing), and when a hidden path names a setting
    its parent requires that nothing fills: it has no default of its own (on the property or its `$ref`
    target) and no enclosing setting's default holds a value for it (`domain/setting_fill.py`). A hidden
    object hides all of its children. The kids story pipeline lists no hidden paths.
  - Any other key names a settings property and holds the hints for it; `items` holds the hints for the
    items of an array property. Nesting follows the settings schema, resolving local `$ref`s (`#/...`) and,
    for an optional property written as `anyOf`/`oneOf`, its first non-null branch (`domain/json_schema.py`).
  - `ui:widget`: one of `textarea`, `select`, `radio`, `checkboxes`, `range`, `color`, `cards` (`UI_WIDGETS`; this
    line is the source both test suites read).
  - `cards` renders a choice field (`oneOf` or `enum`; on any other setting it is a problem) as a radio group of
    selectable cards. Each `oneOf` entry may carry, besides `const` and `title`: `description` (one plain sentence
    shown under the title), `x-group` (a group label; cards with the same label are shown together under it, in
    order of first appearance, and the group labels become a filter) and `x-swatches` (a list of `#RRGGBB`
    colours drawn as swatches on the card). Non-colour swatch entries are ignored. With more than eight options
    the widget also offers a text search over titles, descriptions and group labels. These keys are generic: any
    pipeline may use them, and the web code knows no pipeline's options.
  - `ui:order`: a list of property names of that object. It either names every property or ends with `"*"`
    for the rest; leaving a property out without `"*"` is a problem.
  - `ui:options`: an object; the form honours `rows` on `textarea` and `step` on `range`. A `step` that is not a
    finite number above zero is ignored and the schema's own step is used.
  - No other `ui:` key is allowed. Help text comes from each field's `description` in the settings schema.
    The web mock pipeline uses this same format.
- A settings property whose schema carries `x-machine-local: true` (`MACHINE_LOCAL_KEY` in `domain/ui_schema.py`,
  set with `json_schema_extra`) holds a value that only makes sense on this machine, such as a file or folder
  path. `domain/machine_local.py` finds these properties through nested objects, local `$ref`s and optional
  objects (not inside array items). An export writes the pipeline's default for each of them instead of the
  stored value, and an import replaces each of them with the importing pipeline's default, so paths never move
  between machines. A marked property whose parent object is missing stays missing.
- `PipelineDescriptor` rejects a `ui_schema` with any problem, so a broken plugin fails when it is loaded.
- The `narrated_video` plugin package (`pipelines/narrated_video/`) serves the `kids_story` pipeline type.
- The kids story pipeline (`kids_story`, shown as "Kids story videos") carries no channel identity in its
  defaults: the series name defaults to "Story Time", the brand mark text is empty (no mark is drawn), and
  `{series}` is filled in with the automation's series name in the intro line, outro line, titles,
  descriptions and playlist title; the intro and outro lines take the same placeholders as the description,
  and any placeholder the structure does not supply (including an unknown one) is left empty there, in titles,
  descriptions, playlist titles and the card and thumbnail text (`text/templates.py::render_template` with
  `missing=""`; other callers keep unknown placeholders as written). An episode or Short title that renders
  empty falls back to the script's title, and `UploadMetadata.title` must not be empty. The series name must not be blank in any language. When no bundled story fits the
  automation's cast ids and languages, the story stage fails naming both what the automation has and what
  the bundled stories need.
- Kids story writing, voice and sound controls. Every default renders the translation, motion and judge
  prompts and the story user prompt exactly as before these settings existed, and stored settings without
  them load unchanged. The default editorial rules no longer include "End with the moral said plainly, then
  the series refrain." (the ending requirement states the ending once); that exact line is removed from
  stored `series.editorial_rules` when they load, so the story system prompt only loses that line.
  - `story.tone` (default "warm, gentle") fills "You write <tone>, original stories…" in the system prompt;
    `story.writing_style` is the wording requirement line; each non-blank line of `story.extra_instructions`
    (default empty) becomes one more requirement. `safety.avoid_topics` (default empty) adds a "Never write
    about these topics" list after the editorial rules.
  - `story.ending_style`: `moral_and_refrain` (default), `refrain_only` or `open`. The story prompt, the
    translation rules and the ending gate (and so the `moral_and_refrain` score item) follow it: the moral is
    required only for `moral_and_refrain`, the refrain (when the language has one) for every style but `open`.
    Bundled stories get an empty refrain for `open`; they keep the moral their characters say, because it is
    part of the written dialogue, and no gate runs on them.
  - `story.cast_per_episode` (0, the default, means the whole cast) and `story.lead_mode` (`fixed`: the first
    cast member leads; `per_episode`: the lead is picked from a hash of the run id, as stages have no episode
    counter, so a lead can repeat). The episode cast is the lead followed by the next cast members in cast
    order, wrapping round (`story/casting.py::episode_cast(settings, seed)`). The story prompt lists only the
    episode cast, and the cast gate (`story/checks.py::story_problems(story, settings, seed)`, seeded with the
    run id) rejects any other cast id. Bundled stories are picked against the whole cast.
  - `story.question_style`, `short.hook_style` and `story.translation_style` replace the fixed wording of the
    questions, the hook line and the translation register.
  - `story.enabled_checks`: the story checks that run (`scene_count`, `words_per_scene`, `duration`,
    `ending`, `reading_level`, `cast`, `structure`; default all), published as an array of `oneOf` items with
    `uniqueItems` and shown as checkboxes. Banned words and brand names are child-safety checks: they always
    run and cannot be listed. Translations run the ending check only when it is enabled.
  - Structure counts (`settings/structure_shape.py`, shown only by the structure that uses them):
    `story.item_count` (list and countdown items, default 7, 3 to 15), `story.quiz_questions` (default 4, 1 to
    10) and `story.answer_choices` (choices per quiz question, default 0 for open questions, at most 6; 1 is
    refused: "a quiz question needs no choices or at least two").
  - `sound_effects.max_per_scene` (default 2) is stated in the prompt ("zero to two…", or "always an empty
    list" for 0) and shaping drops any cue beyond it.
  - `voice.speed` is a per-language speed (0.5 to 1.5, default 0.95); a stored single number is applied to
    every language. `voice.narrator_voice` (`settings/narrator_voices.py`) is a per-language voice id
    (default empty: the provider's own default) published as a titled choice per language: empty first, then
    for English the `mlx_audio` presets `warm_storyteller`, `qwen3_narrator`, `news_reader` and the Kokoro voices
    `af_heart`, `af_bella`, `af_nicole`, `am_michael`, `am_fenrir`, `bf_emma`, `bm_george`; for Tamil the
    presets `kayal`, `vaidehi`, `svara_male`. Any other stored string stays valid. Every `mlx_audio` default
    preset is offered for each language it speaks, and every other English choice is in Kokoro's `voices`
    (both enforced by a test). `music.short_mood_prompt` (default empty) replaces `music.mood_prompt` for Short beds.
  - `voice.quality_check` (`NarrationCheck`): `enabled` (default true), `languages` (default `["ta"]`),
    `max_error_rate` (0 to 1, default 0.25) and `retries` (0 to 10, default 2); not in `ui:basic`. For a line
    whose language (primary subtag) is listed, the voice stage compares `Speech.transcript` with the spoken text
    by character error rate (`text/error_rate.py`: NFC, casefolded, punctuation removed, whitespace collapsed,
    Levenshtein distance over the reference length; an empty reference scores 0 against empty and 1 otherwise).
    Above `max_error_rate` the line is spoken again up to `retries` times, retry n written to
    `<language>-<segment>-retry<n>.wav`, stopping at the first pass; the attempt with the lowest rate is kept. Each
    narration artifact records `error_rate` (null when not checked) and `attempts`. The stage logs the rate per
    checked line, a warning when the kept rate is still above the limit, and a note when the voice gave no
    transcript, in which case the line is kept unchecked and the run continues.
  - `visuals.motion_prompt` (with `{action}`, `{visual}` and `{mood}`; `{action}` is the scene's `action`, or its
    `visual` when the action is blank, with trailing full stops and spaces trimmed; a card uses
    "A gentle title card reveal", "a title card" and "warm"; default
    "{action}. Mood: {mood}. Gentle, slow movement, no sudden changes."; a stored value equal to a former default,
    which named `{visual}` instead of `{action}`, loads as the current default of its template) and
    `visuals.judge_criteria` replace the fixed motion and picture-judge wording. A motion prompt naming any
    other lowercase `{placeholder}` fails validation; `$`, `{}` and `{Visual}` pass through as written, as
    does any text in the judge criteria, tone and extra instructions.
- Kids story visual styles. The style library is data: `pipelines/narrated_video/styles/library.json`, validated by
  `styles/library.py`. Each entry has `id`, `title`, `family` (animated, illustrated, drawn, crafted, graphic,
  realistic), `description` (one sentence), `prompt`, `negative_prompt`, `palette` (4 to 6 `#RRGGBB`, ordered
  backdrop or sky first, then land from far to near, accent last), `outline` (none, thin, bold), `texture`
  (smooth, paper, grain, clay, pixel), `motion` (`intensity`, `hero_intensity`, `card_camera`, nullable
  `held_frame_rate`, `feel`, `prompt`: a non-empty declaration of the animation look for video models, and
  `negative_prompt`: non-empty looks the animation must not turn into; drawn, painted, crafted and graphic
  styles avoid "live-action footage", realistic styles avoid "cartoon", and every style avoids text, captions,
  watermark, blurry, distorted, morphing and extra limbs) and `lettering` (`text`, `outline` colours). Ids are unique; adding a style is adding
  one entry. No entry names a studio, brand, film, living artist or trademark.
  - Settings section `look` ("Visual style"): `visual_style` (a library id or `custom`, default
    `watercolour_storybook`, published as `oneOf` cards with `description`, `x-group` = family title and
    `x-swatches` = palette); `custom_style` (`prompt`, required non-blank when the style is `custom`,
    `negative_prompt`, `palette`, `outline`, `texture`, `motion_prompt` and `motion_negative_prompt`, both up to
    400 characters with a generic default); `colour_mood` (style, bright, pastel, warm, cool, night,
    monochrome, custom) with `mood_palette` for custom; `lighting` (style, soft_daylight, golden_hour, moonlight,
    studio, dramatic); `detail_level` (style, minimal, balanced, intricate); `background` (style, plain, simple,
    moderate, rich); `proportions` (style, realistic, cute); `extra_prompt`; `extra_negative_prompt`;
    `use_style_motion` and `use_style_lettering` (both default true). `safety.picture_exclusions` is the
    child-safety negative prompt sent with every picture whatever the style.
  - `styles/resolve.py::resolve_style(settings) -> ResolvedStyle` (style_id, title, prompt, negative_prompt,
    palette, outline, texture, motion, motion_prompt, motion_negative_prompt, lettering) is the one place the look is decided. Prompt: the style prompt
    (for custom: its prompt plus "main colours" naming its palette), then the wording of every non-default
    modifier, then `extra_prompt`. Negative: `picture_exclusions`, the style negative, `extra_negative_prompt`,
    joined with repeated terms dropped. Palette: the style palette shifted by the colour mood, or `mood_palette`.
    Motion and lettering come from the style when the matching switch is on and the style is not custom,
    otherwise from `visuals` (`motion_intensity`, `hero_motion_intensity`, `card_camera`) and `thumbnail`
    (`text_color`, `outline_color`). `motion_prompt` and `motion_negative_prompt` always come from the style's
    `motion` (or the custom style's fields), whatever `use_style_motion` says.
  - Every picture (character sheets, scenes, vertical pictures, thumbnails) and the picture judge use the
    resolved prompt; every `ImageRequest` carries the resolved negative prompt and `style` hints. Motion
    requests use the resolved intensities, card camera, a `held_frame_rate` only when below the episode fps, and
    the resolved `motion_negative_prompt`. The motion prompt is the resolved `motion_prompt` as one sentence
    (skipped when blank), then the rendered `visuals.motion_prompt` (the scene part), then "Camera: <feel>."
    when the feel is set, joined by spaces. Cards, thumbnails and the brand mark
    letter in the resolved lettering colours. The art stage logs the resolved style once and saves it as
    `art/style.json` (artifact kind `text`, meta role `style`, `style_id`, `title`).
  - Stored settings that still hold `series.art_style` or `series.negative_prompt` are migrated before
    validation: the keys are removed; when `look` is absent it is added with both switches off (so stored
    motion and lettering are kept), and a non-default art style or negative prompt becomes
    `visual_style: custom` with those texts as the custom prompt and negative prompt. Any previously valid
    text loads: the custom prompts have no length limit. A missing, blank or non-string art style, or a
    missing or non-string negative prompt, counts as the old default, and both defaults give
    `watercolour_storybook`. When `look` is present the old keys are only removed.
  - `ResolvedStyle.night` is true only for lighting `moonlight` or colour mood `night`. Pictures send it in
    their hints with the scene's visual, setting and mood as `scene_text` (character sheets send none; a
    thumbnail sends its thumbnail text or the first scene's).
- Kids story video look. Every option below defaults to today's output: stored settings without these fields load
  unchanged and give the same ffmpeg command and ASS document.
  - `subtitles`: `karaoke` (default off) colours each word in `highlight_color` while it is spoken, from the
    narration's word timings; `position` (bottom, middle, top; the bottom margin is kept from the top edge at the
    top and ignored in the middle); `bold`; `shadow` (pixels, 0 none); `outline_width` (-1, the default, keeps the
    media provider's outline option; 0 to 20 pixels otherwise; it is the box padding when the box is on);
    `box_background` with `box_color` and `box_opacity` (0 to 1) draws a filled box instead of an outline.
  - `episode`: `intro_card_text` and `outro_card_text` (per language, one line per row; placeholders `{title}`
    `{series}` `{tagline}` `{moral}` `{hook}` `{refrain}`; defaults `{series}\n{title}` and `{refrain}\n{series}`)
    and `card_text_position` (any placement, default centre); `transition` (cut, crossfade, fade_through_black,
    default cut) and `transition_seconds` (above 0, at most 3, default 0.5) for the episode and the Short;
    `video_quality`.
  - `short`: `fps` (0, the default, follows `episode.fps`; otherwise 12 to 60), also used for the Short's motion
    clips; `video_quality`. Quality levels are draft, standard (default: the media provider's CRF), high and best.
  - `thumbnail`: `text_template` (per language, default `{title}`, placeholders `{title}` `{series}` `{moral}`
    `{hook}`, drawn only when `title_text` is on) and `candidates` (1 to 8, default 1). With more than one, every
    candidate is drawn with seeds `base_seed + 5000 + n` and saved as `thumbnail-wide-c<n>.png` (the first keeps
    `thumbnail-wide.png`) and recorded as `candidate` artifacts with `thumbnail: true`; the picture judge picks
    when `use_vision_judge` is on, otherwise the first is kept; the run log records "thumbnail: kept picture k of
    n" and the thumbnail art carries `candidate`.
  - `visuals`: `logo_file` (a .png, .jpg, .jpeg or .webp path on this machine, trimmed, empty default),
    `logo_corner` (default top right), `logo_size_percent` (of the video width, default 12), `logo_opacity`
    (default 0.8), `logo_margin_percent` (of the height, default 3), `logo_on_episode` and `logo_on_short` (both
    default on). Planning the composition does not touch the file; the edit stage checks it just before
    rendering and fails with "visuals.logo_file: no picture at ...". `visuals.logo_file`,
    `subtitles.font_files` and `thumbnail.font_files` are machine-local, so an export carries their defaults.
  - A template with an unknown placeholder is refused on its field (for example `thumbnail.text_template`), and
    the message names the field and the placeholders it may use.
  - Transitions overlap neighbouring segments: each boundary overlaps by `transition_seconds`, cut down to the
    quiet time between the two narrations (the earlier segment's time after its narration plus the later one's
    lead-in, or its whole length when silent) and to half of either segment. Segment lengths stay the same, so
    the video is shorter by the sum of the overlaps, and narration, sound effects and subtitle cues move with
    their segment.
- Every automation language must be one the pipeline offers. Every target language must be in the automation's languages. Every target variant must be one the pipeline offers. Every target channel must exist.
- An automation with schedule `interval` needs `every_hours >= 1`. With `cron` it needs a valid 5-field expression.
- Times of day (`active_from`, `active_until`, `publish_time_of_day`) are 24-hour `HH:MM`. Time zones must exist
  in the system zone database. `active_from` and `active_until` are set together and differ; a cron schedule whose
  every match falls outside its active hours is refused on `schedule.active_from`.
- Automations and runs stored before a field existed load with that field's default, so their behaviour is
  unchanged except that `skip_if_unfinished` is on.
- `review_policy.reject_below` must be below `min_score` when the mode is `auto_when_score_at_least`.
- A target's `publish_time_of_day` cannot be combined with a `publish_delay_minutes` above 0, nor with an explicit
  `private` or `unlisted` privacy (both reported on `targets.<i>.publish_time_of_day`).
- A run snapshots the automation's settings, languages, review policy and retry policy at creation. Editing or deleting the automation never changes a past or queued run.
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
- When `reject_below` is set and the score is below it, the run becomes `rejected` instead, whatever the mode. Its
  review is `rejected` with the notes "Rejected automatically: the score <score> is below the auto-reject threshold
  <reject_below>", and the same text is logged as a warning. A run with no score is never rejected automatically.
- With `auto_publish`, a run publishes as soon as it is approved: at once when the score approves it, and through
  the run queue when a person approves it. It logs "Publishing automatically after approval". When publishing
  cannot start (quota, nothing to publish, automation deleted, pipeline missing, a publish already started), or every upload fails,
  the run stays `approved` and logs a warning "Auto-publish stopped: <reason>" ("no upload succeeded" when every
  upload failed). When some uploads succeed the run is `published` and the failed uploads keep their errors. Without `auto_publish` nothing publishes until a person
  presses Publish. A rejected run never publishes. Auto-publish uses the same upload plan as a manual publish, so
  privacy and made-for-kids follow the same rules.
- When a run fails and it has used fewer than `retry_policy.auto_retry_count` automatic retries, `retry_at` is set
  to the failure time plus `retry_delay_minutes`. Any failure counts, including a run interrupted at startup. On
  the first scheduler tick at or after `retry_at`, the run is re-queued from its first stage that is not done
  (the failed stage), through one atomic run update that also adds 1 to `auto_retries`, and logs "Automatic retry
  <n> of <count> from stage <stage> after: <error>". Re-queuing a run by hand clears `retry_at` and resets
  `auto_retries` to 0, so a run that fails again gets the full allowance of automatic retries. A due automatic
  retry goes ahead even while another run of the same automation is unfinished: `skip_if_unfinished` only governs
  scheduled starts, and the worker pool's parallel run limit caps how many runs execute at once. The message is
  logged only after the re-queue succeeds; a retry that lost a race with a manual retry or a delete logs nothing.
  Automatic retries do not create runs and do not count toward `max_runs_per_day`.
- Only an `approved` run can publish. Publishing creates one upload per target and variant. A target whose language is not in the run, whose channel no longer exists, or that has no matching video yields a `skipped` upload with the reason in `error`. A failed upload fails only itself; the run is `published` when at least one upload is done and none is pending.
- Every upload records the effective `privacy` and `made_for_kids` it was planned with (target value, else the
  channel default; kids pipelines always force made-for-kids), skipped uploads included. Uploads stored before
  these fields existed report them as null.
- Publishing fails closed: when the run's `pipeline_type` no longer resolves to an installed pipeline, publish is
  refused with `pipeline_missing` (409), nothing is uploaded and the run stays `approved`
  (`domain/publish_plan.py::require_publishing_descriptor`).
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
- Scheduled publishing applies only when the effective privacy is `public`. The video is uploaded `private` with
  `publish_at` set, and YouTube keeps it private until then and makes it public at that time. With
  `publish_time_of_day`, `publish_at` is the next occurrence of that wall time in `publish_timezone` strictly after
  publishing starts (today if still ahead, else tomorrow). A time that does not exist that day because clocks go
  forward moves forward by the gap (02:30 becomes 03:30); a time that happens twice because clocks go back uses
  its first occurrence. Otherwise, with `publish_delay_minutes` above 0, `publish_at` is the publish start plus
  the delay. With neither, or when the effective privacy is not `public`, `publish_at` is null and the video gets
  its privacy at once. Every upload records the `publish_at` it was planned with.
- Publishing refuses when the credential's remaining daily quota is below the cost of the upload (1600 units per video, 50 per thumbnail, 400 per caption track, 50 per playlist insertion).
- The quota day resets at midnight Pacific time (`America/Los_Angeles`), as YouTube's does.
- Duplicating an automation creates a disabled copy named with the suffix " (copy)" and new target ids.
- Export and import (`domain/automation_export.py`). An export is an `AutomationDocument`: it never holds ids of
  the automation or its targets, `enabled`, timestamps, run data, credentials, tokens or any secret. Import reads
  the document before anything else: `app` other than "AutoTube" is refused on `app`, and a `format_version`
  above the current one is refused on `format_version` with a message naming both formats and telling the user
  to update AutoTube; both use the message "This file cannot be imported: <reason>.". Any other shape problem
  is a field error at its document path (`automation.languages`). Fields missing from an older export take
  their defaults, and settings are validated and filled like a create. Each target channel resolves, in order,
  to the choice in `channel_map` (a channel id, or null to leave that channel's targets out), the same channel
  id when it exists, or the connected channel with the same `youtube_channel_id`. A chosen channel that does
  not exist is an error on `channel_map.<exported id>`. The automation is then validated exactly like a create,
  with errors prefixed `automation.`, except that a missing target channel is never reported on the target:
  the preview lists it in `unknown_channels`, and the import refuses it on `channel_map.<exported id>`
  ("... choose a channel for its targets or leave them out"). The import creates the automation through the
  create use case, named with the suffix " (imported)" (not added again when the name already ends with it),
  disabled, with new target ids. Unknown keys anywhere in the document (a target `id` included) are field
  errors "Extra inputs are not permitted" at their path.
- A scheduled automation's next run is computed from the later of its last scheduled run, its `updated_at`, and
  the latest `skipped_start_at` among the runs created since its last scheduled run. Manual runs do not move the
  schedule. The schedule gives a candidate start; then, in the schedule's time zone:
  - with active hours, a candidate outside `[active_from, active_until)` moves to the next `active_from` (a window
    whose end is before its start crosses midnight); for a cron schedule the start is then the first match at or
    after that moment. An `active_from` in a clock-forward gap moves forward by the gap.
  - with `max_runs_per_day`, a candidate on a local day that already has that many runs of the automation
    (manual runs included) moves to the next local midnight, then the active hours apply again.
  These limits only shape scheduled starts; Run now is never blocked.
- With `skip_if_unfinished` (on by default), a scheduled start that is due while a run of the automation is
  unfinished (`queued`, `running`, `publishing`, or `failed` with a pending automatic retry) does not start.
  The newest run of the automation gets `skipped_start_at` set to the skipped start (one atomic run update), so
  that start is consumed and the next one follows the schedule, and the unfinished run logs the warning
  "Scheduled start at <YYYY-MM-DD HH:MM> <zone> skipped: run <id> is still <status, or waiting for an automatic
  retry>". Turning it off lets scheduled runs overlap. The mark lives on that run: deleting it loses the mark,
  so the same start can be skipped and logged again on the next tick.
- Each scheduler tick first re-queues the failed runs whose automatic retry is due, oldest first, then starts the
  due automations.
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
- `python -m autotube.doctor` (`just doctor`) prints the report and exits 1 when `can_start` is false
  or an `AUTOTUBE_*` setting is invalid or the system refuses access (an OS error), else 0. It
  creates no file or folder: it does not migrate or create the database, and the file secret store
  creates its key only on the first write. The one change it may make is tightening an existing
  `secrets.key` to mode 0600 when it reads secrets with the file store.
  `python -m autotube.doctor --print-defaults` prints `KEY=value` lines (`DATA_DIR`, `APP_HOST`,
  `APP_PORT`, `REDIRECT_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_URL`, `ACE_STEP_DIR`, `MUSIC_DIR`) that
  `scripts/setup.sh` reads once the backend venv exists; before that it uses the same defaults.
- The OAuth redirect URI is `<redirect base>/api/oauth/callback`. The redirect base is the runtime
  setting `redirect_base_url` when set, otherwise `http://<host>:<port>` with `127.0.0.1` in place
  of a wildcard host (`0.0.0.0`, `::`), so it follows `AUTOTUBE_PORT` in both start modes.
- The file secret store creates its key with an exclusive create (mode 0600); a writer that finds
  the key already created uses it, and a store opened before the key existed reloads it from disk.
- A keychain that cannot be used (locked, or access denied) raises the same 409 `secrets_unreadable`
  as an unreadable secrets file; the message names the keychain error type, never a value.
- App settings come from three places, strongest first: an `AUTOTUBE_*` environment variable that is set
  (`AUTOTUBE_YOUTUBE_CAPTION_TRACK_NAME`, `AUTOTUBE_MAX_RUN_LOG_ENTRIES`, `AUTOTUBE_LOG_LEVEL`,
  `AUTOTUBE_DOCTOR_MIN_FREE_GB`, `AUTOTUBE_CLEANUP_INTERVAL_HOURS`), the stored value, the default.
  A field set by the environment is listed in `locked` with the reason naming the variable. `PUT /settings`
  changes only the fields it sends; a field left out keeps its current value. Saving a locked
  field with a value other than the environment's is a 400 naming the field; saving it unchanged keeps the
  stored value underneath, which applies again once the variable is unset. Settings stored before a field
  existed load with that field's default, and unknown stored keys (such as an old `data_dir`) are ignored.
- Every app setting applies without a restart except the fields in `restart_required`: `log_level` sets the
  `autotube` loggers when the app starts. The caption track name is read at each caption upload, the run
  log cap at each log call, the doctor threshold at each doctor report, the cleanup interval at each
  scheduler tick and `max_parallel_runs` at each worker poll. Tuning internals (tick and poll intervals,
  queue sizes, chunk sizes, database timeouts) stay environment-only. Secrets are never app settings.
- Retention. Final outputs are artifacts of kind `video`, `thumbnail`, `subtitle` or `metadata` that have a
  language; every other artifact and the run's workspace are working files. A run's age counts from
  `finished_at`, or `created_at` when it has none.
  - The cleanup never touches a run that is `queued`, `running`, `awaiting_review`, `approved` or
    `publishing`, nor a `failed` run with a pending `retry_at` (it is still unfinished), nor a run with a
    `pending` or `uploading` upload, nor one with an upload whose `publish_at` is still in the future.
  - Uploads stored before `publish_at` existed do not say whether they were scheduled. A `done` upload
    without `publish_at` whose privacy is `public` or unknown holds its run until the latest time it could
    have gone public under its target's current rule: with `publish_time_of_day`, the next such time in
    `publish_timezone` after `finished_at`; otherwise `finished_at` plus `publish_delay_minutes`. When the
    target no longer exists or its time zone is unknown the release time cannot be known and the run is kept
    until it is deleted by hand. Private and unlisted uploads never hold a run.
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
`ChannelRepository` (get, find_by_youtube_id, list, save, delete),
`TemplateRepository` (get, find_by_type_id, type_id_of(template_id) -> the stored row's type id even when its
payload no longer decodes, or None, list ordered by `created_at`, add, update, delete; add refuses a
stored id with `RuleConflict("template_exists")`; add and update refuse a type id held by another template with
`RuleConflict("template_type_taken")`; get, list and find_by_type_id skip stored rows that no longer decode, so one
bad row never breaks `GET /pipelines`), `ProviderConfigRepository` (list, save_all),
`AppSettingsRepository` (get, save), `QuotaLedger` (used_today(credential_id, day), record(credential_id, units, day)),
`SecretStore` (get, set, delete, has), `Clock` (now), `IdGenerator` (new), `PipelineRegistry` (list, get),
`EngineCatalog` (list, get(engine_id) -> PipelineEngine or None; the installed template engines),
`ProviderCatalog` (descriptors, secrets, option_errors(configs) -> {path: message},
resolver(configs) -> ProviderResolver), `YouTubeGateway` (authorization_url,
exchange_code, describe_channel, upload_video, set_thumbnail, upload_captions, add_to_playlist, list_playlists),
`ArtifactStore` (workspace for a run, save, open, discard one artifact, delete run),
`RunFileStore` (run_ids on disk, usage(run_id, final_ids) -> FileUsage, remove_intermediate(run_id, final_ids)
-> bytes freed, delete_run(run_id) -> bytes freed or a failure when the folder is still there,
disk() -> DiskSpace; every removal is idempotent and never follows a symbolic link out of `runs/`),
`RunQueue` (enqueue, cancel),
`RunEvents` (publish, subscribe), `ScheduleCalculator` (next_run_at(schedule, after, started_on) where
`started_on(local date) -> int` counts the automation's runs created that day in the schedule's zone),
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

`pipelines/registry.py` is the index of installed plugins: `installed_pipelines() -> tuple[Pipeline, ...]` and
`installed_engines() -> tuple[PipelineEngine, ...]`.

### Pipeline templates and engines (`domain/pipeline_templates.py`, `domain/pipeline_engine.py`)

A pipeline template is data that an engine turns into a pipeline type. Domain, api and web treat its
`definition` as opaque JSON described by the engine's definition schema.

```
class PipelineEngine(Protocol):
    engine_id: str
    name: str
    definition_model: type[BaseModel]
    definition_ui_schema: JsonObject
    def blank(self, audience) -> JsonObject
    def problems(self, template) -> dict[str, str]
    def revision_problems(self, current, proposed) -> dict[str, str]
    def pipeline(self, template) -> Pipeline
    def builtin_templates(self) -> list[PipelineTemplate]
```

- `problems` maps a field path (`definition.<path>`, or `engine` for a template of another engine) to a message.
- `revision_problems` reports the definition fields the engine fixes at creation that an update would change,
  keyed the same way. Updating a template returns 400 with these, its `problems` and the rule errors below.
- `type_id` is fixed at creation: `t_<id>` for a user template, the engine's own id for a built-in. A rename never
  changes it.
- Rules (`domain/template_rules.py`): built-ins are read-only (`template_builtin`); audience, engine and type id
  cannot change on update (`revision_errors`); `revised` increments `revision` and keeps id, origin and
  `created_at` without re-checking; on creation
  and on every update the name must not be blank and is at most 80 characters, measured after trimming
  surrounding spaces; a type id already served is refused (`template_type_taken`).
- Built-ins are packaged with their engine (origin `builtin`, status `ready`, revision 1) and never stored.
  User templates are stored in the `pipeline_templates` table (`id`, unique `type_id`, `status`, `created_at`,
  JSON `payload`), added by migration `0002`.
- The `narrated_video` engine has one built-in, `kids_story` (audience kids, empty definition), served by the
  kids story pipeline, so its descriptor is the plugin's own. A stored template is served by the same stages
  under a derived descriptor (below).

#### Narrated definition (`pipelines/narrated_video/template/definition.py`)

`NarratedDefinition` is flat, forbids extra fields, and every field is optional. An empty definition means
"engine defaults"; an empty string, list or language means "do not override".

| Field | Type | Maps to |
| --- | --- | --- |
| `structure` | `story` (default) \| `explainer` \| `list` \| `countdown` \| `quiz` (see Structures) | `story.structure`, pinned; fixed once created (`revision_problems` reports `definition.structure`) |
| `brief` | text, at most 2000 | `story.extra_instructions` as "Every video is about: <brief>" |
| `length` | `short` \| `standard` (default) \| `long` | story and explainer: short 60 s ±15, 4–6 scenes; long 300 s ±45, 14–18 scenes. List, countdown and quiz (fixed scene count, length derived, see Structures): short 10–20 English and 6–14 Tamil words per scene; long 40–80 English and 30–60 Tamil. Standard changes nothing |
| `tone` | text | `story.tone` |
| `topics` | list of text | `story.themes` |
| `visual_style` | a style library id | `look.visual_style` |
| `music_mood` | text | `music.mood_prompt` |
| `title_template`, `short_title_template`, `description_template` | `{en, ta}` text | `metadata.*` per non-empty language |
| `tags`, `hashtags` | `{en, ta}` lists | `metadata.*` per non-empty language |
| `category` | YouTube category, default Film & Animation | `metadata.category` |
| `basic` | dotted settings paths | the derived `ui:basic`; empty keeps the engine's list |
| `hidden` | dotted settings paths | added to the derived `ui:hidden` |
| `settings` | sparse JSON object | merged over everything above |

#### Derived settings model (`template/settings_model.py`)

- `settings_model_for(definition, audience)` builds a subclass of the engine settings model with
  `pydantic.create_model`. Its schema equals the engine's; only the top-level section defaults change.
- Defaults are deep-merged in this order (objects merge, lists and scalars replace): engine defaults, the
  audience defaults (general only: `template/general_defaults.json`), the structure's defaults, the values mapped
  from the definition,
  then the `settings` overlay; the kids floor is applied when the result is validated (kids only).
- The general defaults leave nothing child-directed: tagline, an empty refrain, intro and outro lines,
  editorial rules, the `ink_and_wash` style, a single adult cast member (`mira`), tone, writing style, an open
  ending, themes, morals, question style, judge criteria, the motion prompt default, music mood, sound-effect
  prompt, description, tags and hashtags. A test screens every text default of a blank general template.
- `safety.audience` (`kids` | `general`, default `kids`) is pinned: a before-validator forces the template's
  audience whatever the input says. For general templates `story.source` is pinned to `llm_with_fallback` the
  same way. The `kids_story` pipeline uses the same pinned model with audience kids, so stored `kids_story`
  settings validate unchanged.
- The descriptor's `default_settings` come from this model.
- `story.structure` is pinned the same way to the definition's structure, and `story.source` to
  `llm_with_fallback` for every structure without bundled scripts.
- Derived models are cached per (definition, audience), and the engine schema used by `problems` is built
  once, so checking a template or listing pipelines does not rebuild models or schemas.

#### Derived descriptor

- `type_id`, `name` and `description` from the template (an empty description falls back to the engine's);
  `version` is `"<engine version>+r<revision>"`.
- `ui_schema` is the engine's with `ui:basic` from the definition (or else the structure's or the engine's list,
  without the structure's hidden paths and followed by its shown paths) and `ui:hidden` = the
  definition's `hidden`, then `safety.audience`, then for general templates `story.age_min`, `story.age_max`
  `story.reading_level` and `story.source`, then the structure's hidden paths (see Structures), leaving out
  the structure's shown paths. The engine's own `ui:hidden` is `["safety.audience", "story.structure",
  "story.item_count", "story.quiz_questions", "story.answer_choices"]`: the counts of the other structures, so
  the plain `kids_story` pipeline and a kids story template look the same.
- Capabilities: a kids template keeps `kids_content`; a general template never has it. `domain/kids_rules.py`
  stays the only place that decides the upload's made-for-kids flag.

#### Audience

- Kids floor (`template/kids_floor.py`), applied by the kids-pinned model's before-validator to everything it
  validates: template defaults, automation settings, stored snapshots and the built-in `kids_story`. Neither a
  definition, an overlay nor an automation edit can weaken it:
  - the engine's banned words, brand names and the "No violence, fear, danger…" editorial rule are appended if
    missing (compared ignoring case, never duplicated);
  - every engine `picture_exclusions` term is appended if missing;
  - `story.enabled_checks` always contains `reading_level`, the only switchable check that guards
    age-appropriate language (scene count, words per scene, duration, ending, cast and structure are form
    checks);
  - `story.age_min`/`age_max` stay capped at 12 by validation.
  The banned-word and brand gates are always on, and kids templates of every structure always use the kids
  system prompt (`story_system.txt`, with the age range and reading level).
  Behaviour change: a stored kids automation whose settings removed a floored entry gets it back silently when
  it is loaded; defaults that already meet the floor are unchanged.
- General templates: every prompt with a `_general` variant (`story_system`, `translate_system`, `image_scene`,
  `image_thumbnail`, `judge`) is chosen by audience (`audience_prompts.py`); the story system prompt has no age
  range or reading level and says "The audience is general: the script must never address children…"; an open
  ending lets "viewers" rather than "children" wonder what happens next. The kids prompts are unchanged and
  pinned, and the general prompts are pinned in `tests/fixtures/prompts/general/`; the reading-level gate does not
  apply; upload metadata records `made_for_kids: false` and the metadata score check expects the audience's
  value instead of `true`.
- Child-directed term screen (`story/child_terms.py`, terms in `story/child_terms.json`, English and Tamil,
  case-insensitive whole-phrase match, so "kidney" and longer inflected Tamil words do not match): a heuristic,
  not a guarantee. For general templates it runs:
  - when a template is checked (`template/term_screen.py`): on the name, the definition's `brief`, `tone`,
    `topics`, `music_mood`, metadata templates, tags, hashtags and the chosen style's library text, and on every
    text in the `settings` overlay except the `safety` section (including the chosen style's text). Every
    language present is screened. Each hit is reported where the text was written: `name`,
    `definition.<field>` or `definition.settings.<section>.<field>`;
  - as an always-on script gate on every written and translated script, together with the series intro and
    outro lines in the script's language;
  - in the package stage (`publishing/audience_check.py`), on each upload's title, description, playlist title,
    tags and hashtags. A hit fails the stage, so edits made on a general automation cannot reach an upload.
  Uploads stay private and reviewed by default.
- A general template never uses the bundled stories, which are children's stories: when the writer is missing,
  fails or never passes the gates, the story stage fails with "…never falls back to the bundled children's
  stories" instead.

#### Structures (`pipelines/narrated_video/structures/`)

A structure is the shape of every script. `settings.story.structure` (`story` by default, so stored settings and
the built-in `kids_story` are unchanged) selects one `StructureSpec` from `structures/registry.py::SPECS`:

```
StructureSpec   id, title, wording ({format, pieces, piece}: the words the shared story_system and
                story_user prompts use for this structure), prompt_values(settings, language, seed) -> the
                structure's own story_user values (structure_rules, ending, speaker, characters), translation_rules(settings, language) -> its translation rule lines,
                extra_gates(seed), translation_gates, score_rules, placeholders (metadata placeholders beyond
                the common ones), placeholder_values(story, settings), uses_bundled (may fall back to the
                bundled stories), basic_paths (the derived `ui:basic` when the definition has none; empty
                keeps the engine's), hidden_paths (added to the derived `ui:hidden`), shown_paths (engine
                hidden paths this structure shows again), defaults_files (JSON files in `structures/`,
                merged in order after the audience defaults), fixed_scenes(settings) -> the exact scene
                count, or none (the configured `story.scene_count_min` to `story.scene_count_max`)
```

- Explainer, list, countdown and quiz are built by `structures/shape_spec.py::shape_spec(Shape(...))`: their
  structure gate (after any leading gates, the explainer's moral gate) is both the written and the translation
  gate and the `structure` score item; translation rules are a fixed list (`castless.py::fixed_rules`); the
  prompt values are `castless.py::castless_values(prompt file, fields)` (no ending, speaker or example
  character); hidden paths start with the cast paths; defaults are `castless_defaults.json` (empty refrain,
  cast and morals) then `<structure>_defaults.json`. The intro and closing framing check of list and quiz is
  `framing.py::framing_problems`.

- Length (`structures/length.py`): `scene_range(settings)` is the fixed count twice, or the configured range;
  the prompt says "Exactly N scenes." or "Between A and B scenes.", and the scene count gate says "use exactly N
  scenes, not M" or "use between A and B scenes, not M". `duration_target(settings, language)` is the
  configured `story.target_duration_seconds` and `story.duration_tolerance_seconds`, or, for a fixed count, the
  middle and half-width (rounded) of the window "scenes × words per scene min to max, at the speaking rate"
  clipped to 30–600 s (the bounds of `target_duration_seconds`). The prompt's "about N seconds", the duration
  gate and the episode duration score item (the union of the windows of the run's languages) all use it.
  `length_problem(settings)` reports a fixed count whose window misses 30–600 s in any language ("N scenes read
  in A to B s in <language> at these words per scene, but an episode lasts 30 to 600 s; choose another length
  or count"): it is a settings validation error of every template settings model and the template problem
  `definition.length` at save.

- Script checks (`story/checks.py`): the size gates (scene count, words per scene, duration), then the
  structure's extra gates, then the safety gates (banned words, brand names, child-directed terms), then the
  reading level. Translations run the structure's translation gates, then the safety gates.
- Score items: subtitle timing, episode and Short duration, speaking rate and reading level, then the
  structure's score rules, then metadata limits, loudness and completeness.
- Metadata placeholders: `{title} {series} {tagline} {theme} {questions} {hashtags} {hook}` for every structure,
  plus the structure's own. The descriptions of `metadata.title_template`, `short_title_template` and
  `description_template` name every structure's own placeholders (tested).
- Script model (`story/model.py`): `moral` is optional (default empty) on the draft, the stored script and the
  translation text; `story` and `explainer` still require it through an always-on gate ('write the moral in
  "moral"'), on written and translated scripts. Every scene also carries optional `number` (an integer from
  1, default null: the item's number in a list) and the scene labels `heading`, `question`, `choices` (list)
  and `answer` (default empty), so stored scripts validate. The banned-word, brand-name and child-directed
  term gates read every label with the narration, and the kids reading level gate reads each non-empty
  label as one more sentence after the narration (`story/reading.py::reading_text`). The translation text has optional `scene_labels` (one
  `{heading, question, choices, answer}` per scene): it is sent, and required back with one entry per scene
  ("translation must keep one scene_labels entry per scene"), only when the script has any label; otherwise it
  is left out of the translation prompt, which stays pinned, and ignored in the answer. Numbers are not
  translated.
- Every scene of every structure carries `action` (text, default empty, so stored scripts and bundled stories
  validate): "One short present-tense sentence naming the single visible movement in this scene, for the
  video model." Every script prompt asks for it right after `visual`, with a kids example (a little fox on a
  riverbank) or, for general audiences, a neutral one (a baker at an oven), and shows it in the JSON shape. The
  motion prompt fills `{action}` with it. The banned-word, brand-name and child-directed term gates read it with the
  narration.
- Every structure shares `story_system.txt` (or its `_general` variant) and `story_user.txt`; a structure fills
  `$format`, `$pieces` and `$piece`, puts its own block in `$structure_rules`, and may add the ending and
  speaker requirements and the example character id. The rendered story prompts are unchanged and pinned.
- `story`: wording "animated story" / "stories" / "story"; `$structure_rules` is `story_cast.txt` with the
  episode cast, lead and morals; the ending requirement, the speaker line and the lead as example character; ending and cast
  gates; ending translation gate; `moral_and_refrain` and `character_consistency` score items; placeholders
  `{moral} {characters} {refrain}`; bundled fallback. Its cast needs at least one member (validated on the
  settings, "a story needs at least one cast member"); other structures may have an empty cast.
- `explainer`: a narrated explanation of one topic with no recurring characters. Wording "narrated explainer" /
  "explainer scripts" / "explainer script"; `$structure_rules` is the `explainer.txt` fragment, with no ending
  or speaker line and an empty example character list. The fragment says the first
  scene asks the question the video answers, the middle scenes explain it, the last scene recaps and says the
  takeaway word for word; `moral` holds the takeaway; `characters` is empty and `speaker` is the narrator.
  Gate (check `structure`, in `story.enabled_checks`): the first narration contains a question mark ("open the
  first scene with the question this video answers") and the last scene contains the takeaway ("say the
  takeaway, word for word, in the last scene"); translations run the same gate, and their prompt names no
  characters ("none, there are no recurring characters"). The ending and cast gates do not run, and the
  `moral_and_refrain` and `character_consistency` score items are not scored; the `structure` item ("Explainer
  hook and takeaway", weight `quality.weights.structure`, default 1.5) scores the explainer gate the way the
  ending item does. Placeholder `{takeaway}`. No bundled fallback: `story.source` is pinned to
  `llm_with_fallback`, and when the writer fails the story stage fails ("…explainer scripts have no bundled
  fallback" for kids, the general message for general). Defaults (`structures/explainer_defaults.json`): an
  empty cast and refrain, explainer topics as themes, no morals, a "Do you remember?" question style, and an
  explainer description (with `{takeaway}`), tags and hashtags, all free of child-directed terms. Hidden paths:
  `cast`, `story.morals`, `story.ending_style`, `story.ending_scenes`, `story.lead_mode`,
  `story.cast_per_episode`, `series.refrain`, `visuals.character_sheets`, `quality.weights.moral_and_refrain`,
  `quality.weights.character_consistency`, and `story.source`.

- `list`: a numbered list of `story.item_count` items (default 7, 3 to 15, hidden for other structures) on one
  topic, with no recurring characters. Wording "numbered list" / "list scripts" / "list script";
  `$structure_rules` is `numbered_list.txt`: an intro hook scene, then one item scene per item numbered from 1
  up, each with `number` and a `heading` in the script's language and narration that starts with the number,
  then a closing scene; intro and closing have no number; headings differ; `moral` is empty; no characters.
  Fixed scenes: items + 2 (the scene counts and the target duration and tolerance are hidden). Gate (check
  `structure`): first and last scenes unnumbered ("open with an intro scene and end with a closing scene, both
  without a number"), exactly `item_count` numbered scenes ("write exactly N numbered items, not M"), numbers
  1..M in scene order ("number the items from 1 up to M, in that order"), every item has a heading ("give
  every item a short heading") and no heading repeats, ignoring case ("give every item its own heading").
  Translations run the same gate and are asked for `scene_labels` and to keep the headings different and
  the numbers in the narration. Score item `structure` ("List numbering and headings"). Placeholders
  `{count}` (numbered scenes) and `{items}` (their headings, comma-separated, in scene order). No bundled
  fallback ("…list scripts have no bundled fallback"). Defaults (`structures/list_defaults.json`): empty cast
  and refrain, "facts about …" topics, no morals, a "Do you remember?" question style, a description with
  `{count}` and `{items}`, tags and hashtags free of child-directed terms. Hidden paths: the explainer's cast
  paths, the scene counts, `story.target_duration_seconds` and `story.duration_tolerance_seconds`; shown path
  `story.item_count` (so in the Simple view it replaces the target duration).
- `countdown`: the list with one change of direction (`structures/numbered.py::numbered_spec(..., descending)`
  builds both). Wording "countdown" / "countdown scripts" / "countdown script"; the same fragment numbers the
  items "from N down to 1, so the last item is number 1", and the gate wants that order ("number the items
  from M down to 1, so the last item is number 1"). Score item "Countdown numbering and headings"; the same
  placeholders (`{items}` in video order, so number one last), hidden and shown paths. No bundled fallback.
  Defaults (`structures/countdown_defaults.json`): ranking topics ("the fastest animals", …), a countdown
  description, tags and hashtags.
- `quiz` (`structures/quiz.py`, `structures/quiz_checks.py`): `story.quiz_questions` questions on one topic, with
  no recurring characters. Wording "quiz" / "quiz scripts" / "quiz script"; `$structure_rules` is `quiz.txt`:
  an intro hook scene, then one question scene and its reveal scene per question, then a closing scene. A
  question scene's `question` holds the question (ending with a question mark) that its narration asks; with
  `story.answer_choices` > 0 its `choices` lists that many short answers, one of them the answer, read out in
  the narration, and with 0 `choices` is empty (open questions). The reveal scene's `answer` holds the short
  answer, which its narration says word for word and explains in one sentence. `heading` is empty, `number`
  null, `moral` empty. Fixed scenes: 2 × questions + 2. Gate (check `structure`): intro and closing
  scenes carry no question or answer ("open with an intro scene and end with a closing scene, with no question
  or answer"); exactly `quiz_questions` question scenes ("ask exactly N questions, not M"); for question K:
  "end question K with a question mark" (`?` or `？`), "follow question K with a reveal scene that gives its
  answer" (the next scene has a non-empty answer), "say the answer to question K, word for word, in its
  reveal", "give question K exactly C choices" or "ask question K as an open question, with no choices", and
  "make the answer to question K one of its choices" (ignoring case). Translations run the same gate (so
  Tamil questions keep their question mark and Tamil answers appear in their reveals) and are asked for
  `scene_labels`. Score item `structure` ("Quiz questions and reveals"). Placeholder `{question_count}` (the
  question scenes). No bundled fallback ("…quiz scripts have no bundled fallback"). Defaults
  (`structures/quiz_defaults.json`): general-knowledge topics, a quiz description with `{question_count}`,
  tags and hashtags. Hidden paths: as for the list; shown paths `story.quiz_questions` and
  `story.answer_choices`.

- Safety across structures (tested): a kids template of any structure carries `kids_content`, uploads made for
  kids, keeps the kids floor and the kids system-prompt lines; a general template of any structure never does;
  a general explainer, list, countdown or quiz runs the child-directed term gate and never uses the bundled stories; a blank template of
  every structure and audience has no problems and runs offline through the fake providers.

#### Problems

`engine.problems(template)` returns, keyed by field path: definition validation errors (`definition.<field>`);
an unknown style (`definition.visual_style`, reported alone); placeholders the structure does not supply in the
metadata templates (`definition.title_template`, `definition.short_title_template`,
`definition.description_template`, and the overlay's `definition.settings.metadata.<field>` for those and
`playlist_title`; the message names the field, the unknown placeholders and the usable ones, the common
placeholders plus the structure's; see Structures); `ui:basic`
and `ui:hidden` rule failures against the derived ui schema (`definition.basic`, `definition.hidden`); overlay
validation errors (`definition.settings.<path>`, skipped when `definition.length` is reported, see Length under
Structures); term screen hits (see Audience); and `engine` for a
foreign template. An invalid definition returns only its own errors.

Template use cases (`application/*_template*.py`, sharing `application/template_lookup.py`) reach engines only
through `EngineCatalog`, which the composition root builds from `installed_engines()`
(`infrastructure/pipelines/engine_catalog.py`). They treat `definition` as opaque and validate it only through
`engine.problems(template)`.

- A template id is looked up among the engines' built-ins first (a built-in's id is its type id), then among
  stored templates (`found_template`). An unknown id, or a stored row that no longer decodes, is
  `template_not_found`, except for delete. The taken type ids are the served pipeline types plus every built-in's
  (`taken_type_ids`). The built-ins of all engines come from `domain/pipeline_engine.py::builtin_templates_of`,
  which the template registry uses too.
- A template is in use (`domain/template_usage.py`) while any automation's `pipeline_type` is its type id,
  enabled or disabled, or while any open run has it as `pipeline_type`. A run is open when it is queued, running,
  publishing, awaiting review or approved, or failed with a pending automatic retry (`retry_at` set).
  `template_in_use` names the automations in name order and the open runs in id order.
- List returns every engine's built-ins, then the stored templates by `created_at`, each as a TemplateSummary.
- Create assigns a fresh id and type id `t_<id>`, revision 1 and `created_at = updated_at = now`, and stores the
  name trimmed. Field errors (400), each checked once: `origin: builtin` and the name rules (`input_errors`),
  then an engine that is not installed (`engine`) or the engine's `problems`. A type id already served or built in is
  `template_type_taken` (409).
- Update replaces name, description, audience, status and definition. A built-in is refused first with
  `template_builtin` (409). Field errors (400), reported together: an audience or engine change, the name rules,
  the engine's `problems` (or `engine` when it is no longer installed); the `origin` sent is ignored and the
  stored origin kept, and a `type_id` in the body is refused by the request schema. Setting a `ready` template to
  `draft` while it is in use is `template_in_use` (409); otherwise any status change is allowed. The revision then
  increments through `revised`.
- Delete refuses a built-in with `template_builtin` and a template in use with `template_in_use`
  (`domain/deletion_rules.py::ensure_template_deletable`). A stored row that no longer decodes is deleted through
  its stored type id with the same in-use check, without decoding. The in-use check and the delete are separate
  reads, so a run started between them is not caught.
- Duplicate works for built-ins and stored templates. The copy has a fresh id and type id, origin `duplicate`,
  status `draft`, revision 1, the source's engine, description and definition, the requested audience or the
  source's, and the requested name or the source name shortened to fit with `COPY_NAME_SUFFIX` " (copy)"
  appended (`domain/copy_names.py`, shared with duplicating an automation). It is validated once: the name rules
  and the engine's `problems` together (400), then a free type id (409 `template_type_taken`).

`infrastructure/pipelines/template_registry.py` holds `TemplatePipelineRegistry(static, engines: EngineCatalog,
templates)`, the
`PipelineRegistry` adapter the composition root builds from the index and the `TemplateRepository`:

- `list()` returns the static pipelines whose type id no engine built-in serves, then every engine's built-ins,
  then the stored templates that are `ready`, belong to an installed engine and have no `problems`.
- `get(type_id)` resolves the same set, a stored template through `engine.pipeline(template)`. The pipeline is
  cached per type id together with the template it was built from, and rebuilt when the stored template differs
  in any field. The entry is dropped when the template is deleted or stops being served.
- A stored template can never shadow a built-in or static type id; such a template is not served.
- Two static pipelines, two built-ins with the same `type_id`, or two engines with the same `engine_id` are
  refused when the registry is built (`infrastructure/pipelines/pipeline_index.py`).
- A stored template's pipeline builds its descriptor once, so listing pipelines does not rebuild schemas.

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
               timing_source: synthesizer | alignment | estimate,
               transcript: what Whisper heard, words joined by spaces (empty when not recognised)
music  MusicGenerator.compose(MusicRequest, output) -> Path
media  MediaToolkit.duration_seconds(media), compose_video(VideoComposition, output) -> Path,
       extract_frame(video, at_seconds, output) -> Path, loudness_lufs(media)
```

- `VideoComposition` and `MotionRequest` width and height are rounded down to the nearest even number
  (minimum 2), as H.264 with 4:2:0 chroma needs even sizes.
- `ImageRequest.style` (nullable `ImageStyleHints` in `domain/image_style.py`: `palette` of `#RRGGBB`, ordered
  backdrop first and accent last, `outline` none|thin|bold, `texture` smooth|paper|grain|clay|pixel) is a
  provider-neutral hint. Prompt-driven models may ignore it. The offline image provider paints with it: sky from
  the first colour, three land layers from the middle colours, flowers and sun from the last; outlines in a
  colour that contrasts with the sky (thin or bold); and a texture pass (paper wash, film grain, soft clay
  relief, or pixels quantised to the palette). Hints also carry `night` (bool, default false) and `scene_text`
  (the scene's own words, default empty). With hints, the offline provider paints night only when `night` is
  set or `scene_text` reads as night; the art direction in the prompt never decides it. Without hints, the
  prompt words decide as before. Night darkens the hinted palette. The same seed gives the same picture; hints
  without colours keep the scene-derived palette.
- `MotionRequest.held_frame_rate` (nullable, at least 1): when below `fps` the clip changes picture only that
  many times a second (a held, stop-motion feel) while keeping `fps`. The ffmpeg pan-and-zoom and LTX providers
  honour it; DepthFlow ignores it.
- The default motion order is `ltx_mlx`, `depthflow`, `ffmpeg_pan_zoom`. `ltx_mlx` runs the `ltx-2-mlx generate`
  command and is unavailable when its command or ffmpeg is not on PATH or its model folder does not exist. It
  generates at the landscape size, or the portrait size when the request is taller than wide. The duration is
  split evenly into the fewest segments no longer than `max_segment_seconds`; each segment has the smallest 8k+1
  frame count covering its length at `frame_rate`. The first segment starts from the request image, each later
  one from the previous segment's last frame (`ffmpeg -sseof -0.05`). One ffmpeg pass then joins the segments,
  scales and crops to the request size, converts to `fps`, applies `held_frame_rate`, and trims to the duration.
  Intermediates live in a temporary folder next to the output and are removed afterwards; a run that writes no
  output is an upstream failure. Options (each with title and description): `binary`, `model_dir` (default
  `~/.autotube/models/reverie-studio__ltx-2.5-mlx-q4-distilled`), `distilled` (passes `--distilled`, default
  true), `text_encoder` (`--gemma`, omitted when empty), `negative_prompt` (the fallback used when
  `MotionRequest.negative_prompt` is empty), `use_nag` (passes `--nag` and the request's negative prompt, or the
  option when the request has none), `seed`, `frame_rate`, `landscape_width`/`landscape_height` (704x384) and
  `portrait_width`/`portrait_height` (384x704), multiples of 64, `max_segment_seconds` (3), `image_strength`,
  `hf_home` (default `~/.autotube/hf`, sets `HF_HOME` when not empty), `hf_offline` (sets `HF_HUB_OFFLINE=1`),
  `ffmpeg_binary`, `crf`, `preset` and `timeout_seconds` (per command, 1200). A leading `~` in `model_dir` and
  `hf_home` is expanded to the home folder when used (availability check, `--model`, `HF_HOME`).
- `MotionRequest.negative_prompt` (default empty) names looks the clip must avoid. Providers without negative
  prompting ignore it.
- Ducking lowers the music only while narration plays; the music continues at its set volume after
  the last narration clip.
- `extract_frame` fails with an upstream failure when no frame was written, for example past the end.
- Speech synthesizers refuse blank text with an upstream failure.
- The `mlx_audio` TTS provider (first in the TTS registry order, before `edge_tts`) speaks with named voice presets
  (`presets`: id -> name, model folder under `models_root`, languages, generation kwargs, sentence_split,
  pause_ms). `SpeechRequest.voice` names a preset; empty means `default_voice` for the request language
  (en `warm_storyteller`, ta `kayal`). No default for the language is an upstream failure
  `language_unsupported`, an unknown preset `voice_unknown`, and a preset that does not list the language
  `language_unsupported`. mlx-audio is not an app dependency: the provider runs
  `<python> -I mlx_audio_worker.py` from a separate venv with `HF_HOME=<hf_home>` and `HF_HUB_OFFLINE=1`,
  passing a JSON job `{model_dir, text, kwargs, sentence_split, pause_ms, output}` on stdin. The worker writes
  mono 16-bit PCM WAV at the model's rate; with sentence_split it speaks each sentence (split after `.`, `!`,
  `?`, `।`, `॥`) and joins them with pause_ms of silence. Word timings are estimated, then refined with
  Whisper alignment, which also fills `Speech.transcript` even when the timings are rejected. It is unavailable when `python` or `models_root` does not exist, so hosts without
  them fall through to the next TTS provider. `python` (default `~/.autotube/venvs/mlx/bin/python`),
  `models_root` (default `~/.autotube/models`) and `hf_home` (default `~/.autotube/hf`) expand `~` when used.
- A TTS provider refuses a requested voice it cannot speak with an upstream failure `voice_unknown`, so the
  fallback chain passes the request on: `edge_tts` refuses a voice not matching `voice_pattern` (default
  `^[a-z]{2,}-[A-Z]{2,}-.+Neural$`; an invalid regular expression fails option validation), and `kokoro`
  refuses a voice not in `voices` (default the Kokoro v1.0 voice ids). With the default order a Kokoro voice
  therefore falls through `mlx_audio` and `edge_tts` to `kokoro`, and an `mlx_audio` preset is spoken by
  `mlx_audio`. An empty voice uses each provider's own default.
- `SubtitleStyle` (`domain/video_look.py`): burn_in, font_family, font_file (nullable), font_size, primary,
  outline and highlight colours, margin_bottom, margin_sides, wrap_lines (default false), karaoke (default
  false), position (bottom|middle|top, ASS alignment 2, 5, 8; margin_bottom is the vertical margin from that
  edge), bold, shadow (pixels), box (default false), box_color, box_opacity, outline_width (nullable: null uses
  the provider's outline option). The ASS style keeps today's fields when all of these are at their defaults;
  a box uses border style 3 with the box colour and opacity in the outline colour.
- `VideoComposition` also carries `subtitle_words` (word timings in timeline seconds, one per displayed word, in
  order), `transition` (cut|crossfade|fade_through_black, default cut), `quality`
  (draft|standard|high|best, default standard) and `watermark` (nullable `Watermark`: image, corner,
  width_share of the frame width, opacity, margin_share of the frame height).
- With `SubtitleStyle.karaoke`, every entry is still drawn whole on layer 0 in the `Default` style (so a box stays
  one box), and a second style `Spoken` (the highlight colour, no outline, box or shadow, same font, size,
  weight, alignment and margins) draws on layer 1 one event per word, from that word's start to the next word's
  start (the last to the entry's end), with every other word fully transparent so the spoken word lands exactly
  on top. Words belong to the entry they start inside; an entry whose words do not match its displayed words one
  for one gets no layer 1 events. Without karaoke the document has no `Spoken` style and no layer 1.
- The ffmpeg toolkit reads overlaps from the visual timeline (a clip starting before the previous one ends).
  Crossfade fades the later clip in over the overlap; fade through black darkens the earlier clip over the first
  half and reveals the later one over the second half; cut draws overlapping clips as they are. The watermark is
  read as one still picture whatever its path holds (`-f image2 -pattern_type none -i file:<path>`), scaled to
  an even width, given the opacity, and overlaid in its corner before subtitles are burned in. Quality
  shifts the provider CRF by +8 (draft), 0 (standard), -4 (high) or -8 (best), kept within 0 to 51.
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
| GET `/automations/{id}/export` | | AutomationDocument |
| POST `/automations/import/preview` | `{document, channel_map?: {exported channel id: channel id or null}}` | ImportPreview; 400 with field errors (see Rules) |
| POST `/automations/import` | same as preview | Automation, 201; 400 with field errors, including `channel_map.<id>` for every unknown channel without a choice |
| POST `/automations/{id}/runs` | | Run, 201 |
| GET `/runs?automation_id&status&limit` | | `[Run]` newest first |
| GET `/runs/{id}` | | Run |
| POST `/runs/{id}/retry` | `{from_stage?}` | Run |
| POST `/runs/{id}/cancel` | | Run |
| POST `/runs/{id}/review` | `{decision, notes?}` | Run |
| POST `/runs/{id}/publish` | | Run; 409 `pipeline_missing` when the run's pipeline is no longer installed |
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
| GET `/template-engines` | | `[EngineSummary]` |
| GET `/templates` | | `[TemplateSummary]`, built-ins first |
| GET `/templates/{id}` | | TemplateSummary; a built-in's id is its type id; 404 `template_not_found` |
| POST `/templates` | `TemplateInput` | TemplateSummary, 201; 400 with field errors; 409 `template_type_taken` |
| PUT `/templates/{id}` | `TemplateInput` | TemplateSummary; 409 `template_builtin`; 400 for an audience, engine or type id change and for field errors; 409 `template_in_use` for ready to draft while automations or open runs use it |
| DELETE `/templates/{id}` | | 204, also for a stored row that no longer decodes; 404 `template_not_found`; 409 `template_builtin`; 409 `template_in_use` naming the automations and open runs |
| POST `/templates/{id}/duplicate` | optional `{name?, audience?}` | TemplateSummary, 201; 400 with field errors; 404 `template_not_found`; 409 `template_type_taken` |

`AutomationInput` is Automation without `id`, timestamps and derived fields. Target `id` is optional on input.

The built UI is served at `/`. A path without a file extension that matches no file returns `index.html`;
a missing path with an extension (such as `/assets/missing.js`) and any `/api` path return the 404 envelope.

## UI

Routes: `/` dashboard, `/automations`, `/automations/new` (optional `?pipeline=<type id>` chooses that
pipeline type when it is served), `/automations/:id`, `/pipelines`, `/pipelines/new`, `/pipelines/:id`,
`/runs`, `/runs/:id`, `/channels`, `/providers`, `/settings`.

- Automations list: name, pipeline, languages, targets, schedule, next run, last run status, enabled switch,
  actions (run now, edit, duplicate, export, delete with confirmation). Export downloads
  `<name slug>.autotube.json` (accents dropped, lower case, every other run of characters becomes "-",
  trimmed, "untitled" when nothing is left). Import (list header and empty state) opens a dialog: choosing a
  file runs the preview; a file that is not a JSON object, a refused format and field errors are shown in the
  dialog, each unknown channel gets a "Channel for “<title>”" select (every channel, named like the target
  channel select: its title, plus its status label in brackets when it is not connected; or "Leave its targets
  out"), and "Import automation" stays disabled until the preview succeeds. Cancel creates nothing.
- Settings forms with defaults (the editor's Content section passes the pipeline's `default_settings`): every
  field whose value differs from its default shows a "Changed from default" dot and a "Reset" button (its title
  names the default); changes are tracked on named fields, per-language values and other nested fields, whole
  arrays and `cards` choices, never inside array items. A field without a default is never marked. Each
  `ui:sections` section with changes shows "<n> changed" and "Reset section to defaults". Resetting moves focus
  to the field, or to the section title, and space for the controls is reserved so nothing shifts.
- Automation editor: sections General, Content (form generated from `settings_schema` and `ui_schema`),
  Languages (multi-select from the pipeline's languages), Targets (rows of channel, language, variants,
  privacy, playlist, made for kids, and when to go public: at once, after a delay, or at a time of day in a time
  zone), Schedule (kind, active hours, daily cap, skip while unfinished, and automatic retries with their delay),
  Review (mode, minimum score, auto-reject below, publish after approval). Client-side validation mirrors the
  rules; server errors map to fields (`retry_policy.*` errors show in Schedule). The editor shows one
  plain-language summary of the schedule and review rules, for example "Runs every 6 hours, 08:00 to 20:00,
  at most 2 a day. Publishes privately after you approve.", built by a pure function. When a target goes public
  at a time of day, the summary names it ("Goes public at 18:00 (Asia/Kolkata).").
  Each pipeline type in the picker and in the saved automation's summary shows its audience badge: "For kids"
  when its capabilities include `kids_content`, otherwise "General audience".
  A two-way toggle at the top switches between "Simple" (the default) and "All settings"; the choice is
  remembered per browser in localStorage (`autotube.editor.settings-view`), and an unavailable storage falls
  back to Simple. Simple shows, in Content, only the pipeline's `ui:basic` fields under their section titles
  (sections with no basic field are hidden, nested objects show only their basic children, a pipeline without
  `ui:basic` shows its whole form), and in the other sections name, pipeline type, enabled, languages, targets
  (channel, language, privacy, made for kids, outputs), the schedule kind with its hours or cron, and the review
  mode with its minimum score and auto-publish. It hides the finer rules declared in
  `ADVANCED_PLATFORM_FIELDS` (`model/settingsView.ts`): description, schedule timezone, schedule limits, retry
  policy, target playlist, target publish timing and auto-reject. A quiet line says "<n> more options in All
  settings" (hidden pipeline fields plus the finer rules that apply to the draft: timezone and limits only for a
  schedule that is not manual, playlist and publish timing only with at least one target), adds ", <n> changed" for hidden pipeline fields
  changed from their defaults, and offers "Show all settings". The pipeline's `ui:hidden` fields (and a group
  whose every field is hidden) show in neither view, are not counted in "more options" or "changed", and are
  never matched by search or Changed only. Change marks, field resets, section "changed" counts and section
  resets leave hidden fields out: an object's mark and reset (including an optional object's) consider only
  its shown children, and a reset never changes a hidden value. Hidden fields keep their values and still
  validate; when a save fails (client or server) on a field hidden in Simple, the editor switches to All
  settings so the error shows at its field. A pipeline field with an error is always shown, in both views
  and whatever the search or Changed only filter, together with its parent groups. Section "changed" counts and
  section resets show only while the form is unfiltered: no `ui:basic` rule in Simple and no search or
  Changed only in All settings (`ui:hidden` alone does not filter). All settings adds, above the Content form, a search box that filters pipeline fields by
  title and description (a match keeps its parent groups and all its children; sections with no match are
  hidden; array items are not searched) and a "Changed only" switch that keeps fields changed from their
  defaults; both combine. When nothing is left and no setting has an error, an empty state offers
  "Clear search", which empties the search and turns Changed only off. A visible setting whose schema lists no
  properties (an open map) shows all of its entries.
  A saved automation without unsaved changes offers Run now; with unsaved changes it is disabled with the reason.
  A saved automation also offers Export, which always exports the saved version.
  A "Run queued" toast (list or editor) links to the new run; a toast with an action stays until it is
  used or dismissed, other toasts close after five seconds. An unknown automation id shows a not-found
  state with a link back to Automations.
- Pipelines (the UI's name for pipeline templates; nav item "Pipelines"): a list of every template, built-ins
  first, each with its name, description, badges ("Built-in", "For kids" or "General audience", "Draft") and
  "Used by <n> automations" (`automations_using`). Actions: "New automation" (ready templates only; opens
  `/automations/new?pipeline=<type id>`), Edit (View for a built-in), Duplicate, and Delete (not offered for
  built-ins). Duplicate opens a dialog with an optional name (empty sends no name, so the server adds
  " (copy)") and the audience (the source's by default); success opens the copy, a refused name shows at the
  field. Delete asks for confirmation; a 409 `template_in_use` keeps the dialog open and shows the server's
  message, which names the automations and open runs. A 409 conflict (`template_in_use`, `template_builtin`,
  `template_type_taken`) shows as a titled alert with the server's message; other failures show as a toast.
- New pipeline (`/pipelines/new`): first "For kids" or "General audience", with the note that the audience
  cannot be changed later (kids pipelines always upload as made for kids); "Continue" stays disabled until
  one is chosen. Then the form: name (required, at most 80 characters after trimming, checked before
  sending), description, the audience read-only, and the definition rendered by `SchemaForm` from the first
  installed engine's `definition_schema` and `definition_ui_schema`, prefilled from `blank[audience]`. "Save
  as draft" and "Save and make ready" send status `draft` or `ready`; success opens `/pipelines/:id`. Server
  field errors show at their fields, definition errors (`definition.<path>`) inside the form.
- Pipeline (`/pipelines/:id`): a user template opens the same form with the audience read-only, a "Ready to
  use in automations" switch (draft or ready) and "Revision <n>"; "Save changes" keeps the chosen status. A
  built-in opens read-only with "Duplicate to customise", which opens the duplicate dialog. An unknown id
  shows "Pipeline not found" with a link back; a template whose engine is not installed shows a warning
  instead of the form.
- Run detail: live stage timeline, logs, score breakdown, approve or reject with notes, publish, retry from
  stage. A `status` event refetches the open run so score, score details and timestamps update live.
  Artifacts list final outputs first (kinds `video`, `thumbnail`, `subtitle`, `metadata` with a language),
  grouped by language and variant with video players, subtitles and metadata; every other artifact is an
  intermediate file, collapsed per stage in the run's stage order. The uploads table shows each upload's
  privacy, made-for-kids flag and scheduled publish time. Automatic events are called out above the logs:
  an automatic rejection with its reason, a pending automatic retry with its time and attempt, retries already
  made, skipped scheduled starts and stopped auto-publishes. Only run-level logs (no `stage_id`) are read as
  automatic events, by the message prefixes in `docs/spec/automatic-events.json`; backend and web tests both
  check those sample messages against their builders. Cancel is offered for the statuses the Rules allow. When the run's
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
