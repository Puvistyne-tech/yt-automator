# YouTube Automator

A local web app that connects your YouTube channels and runs configurable automations that create
and publish videos. Each automation combines a pipeline type, its settings, target channels,
languages, a schedule and a review rule. The first pipeline type is Kutty Stories: short story
videos for children.

Everything runs on your own Mac at zero cost. Text, images, motion, voices and music come from
local models or free tiers, and every provider has an offline fallback, so the app always starts.

## Quick start on the Mac

Requirements: macOS on an Apple-silicon Mac and [Homebrew](https://brew.sh) (free).

```bash
git clone https://github.com/Puvistyne-tech/yt-automator.git
cd yt-automator
scripts/setup.sh --dry-run --all
scripts/setup.sh --all
```

`--dry-run` prints the plan without changing anything. The script is safe to run again: it skips
what is already installed. Pick only what you need:

| Flag | Installs |
| --- | --- |
| (none) | uv, just, ffmpeg, node, pnpm, backend and web dependencies, the built UI |
| `--ollama` | Ollama as a background service and the app's default model, `gemma3:12b` (set `OLLAMA_MODEL` to pull another model, then choose it in the Ollama provider's Model option under Providers) |
| `--images` | mflux (`mflux-generate`) for FLUX image models on Apple silicon |
| `--motion` | DepthFlow parallax motion (`uv tool install depthflow`) |
| `--speech` | edge-tts, Kokoro, espeak-ng and Whisper alignment (Python extras `tts`, `align`, `mac`) |
| `--music` | ACE-Step in its own venv at `<data dir>/tools/ace-step` and the folder `<data dir>/assets/music` |
| `--fonts` | Noto Sans, Noto Sans Tamil and libraqm for Tamil text shaping |
| `--models` | every model group above |
| `--service` | a launchd agent that starts the app at login; `--uninstall-service` removes it |
| `--all` | the base, every model group and the service |

Model weights download on first use from Hugging Face or Ollama. They are free and need no account,
except gated models such as FLUX.1-dev: accept the licence on huggingface.co, create a read token,
and add it as the `huggingface_token` secret in the UI. The script records the Python extras it
installed in `<data dir>/setup/extras`; `just setup` alone removes them, so run `scripts/setup.sh`
again afterwards.

The script adds `~/.local/bin` (where `just`, `mflux-generate` and `depthflow` live) to your shell
profile with `uv tool update-shell`. Open a new terminal afterwards so the commands are on PATH.
After the backend is installed, the script reads the app's own defaults (data directory, host,
port, Ollama model and URL, music folders) from `python -m automator.doctor --print-defaults`.

Start the app:

- as a service: `scripts/setup.sh --service`, then it starts at every login, or
- by hand: `just dev-api` serves the API and the built UI; `just dev` also starts the Vite dev server.

Open <http://127.0.0.1:8000>. Then add your free API keys (Groq from console.groq.com, Gemini from
aistudio.google.com) under Providers, Secrets. The host, port and data directory come from the
environment: `AUTOMATOR_HOST`, `AUTOMATOR_PORT`, `AUTOMATOR_DATA_DIR`,
`AUTOMATOR_REDIRECT_BASE_URL`. The service bakes in the values present when you install it.

## Check the installation

```bash
just doctor
```

prints every provider with available or not and the reason, the missing secrets, the ffmpeg and
ffprobe versions, the Python version, the data directory and its free space, the database migration
state and whether the UI build exists. It exits non-zero only when the app cannot start at all. A
capability without a usable provider is a warning, because offline providers exist. The same report
is served at `GET /api/doctor`.

## Google Cloud OAuth credentials for the YouTube Data API

Each credential in the app is one Google Cloud project with its own daily quota.

1. Open <https://console.cloud.google.com>, create a project (free, no billing needed).
2. APIs and services, Library: enable **YouTube Data API v3**.
3. OAuth consent screen (Google Auth Platform): user type **External**, fill in the app name and
   your email. Add the scopes `youtube.upload`, `youtube.readonly` and `youtube.force-ssl`.
4. Audience: leave the app in **Testing** and add every Google account that owns a channel you
   will connect as a **test user**. In Testing, Google expires the authorization after 7 days;
   the channel then shows as expired and you reconnect it in one click.
5. Clients: create an OAuth client of type **Web application**. Under Authorised redirect URIs add
   exactly `http://127.0.0.1:8000/api/oauth/callback`. The redirect URI follows the port: with
   `AUTOMATOR_PORT=9000` register `http://127.0.0.1:9000/api/oauth/callback` instead. It is
   `http://<host>:<port>` (127.0.0.1 when the host is `0.0.0.0` or `::`) followed by
   `/api/oauth/callback`, unless `AUTOMATOR_REDIRECT_BASE_URL` sets the base explicitly. If you
   change the port later, update the URI in Google Cloud too. To see the base in use, run
   `cd backend && uv run python -m automator.doctor --print-defaults` and read `REDIRECT_BASE_URL`.
6. Copy the client id and client secret.

Quota: each project gets 10,000 units per day, reset at midnight Pacific time. One upload costs
about 1,600 units, a thumbnail 50, a caption track 400 and a playlist insertion 50, so a project
publishes about four fully dressed videos a day. Add more credentials for more channels. The app
refuses to publish when the remaining quota is too low.

## Connect a channel

1. Channels, Add credential: paste the client id and secret. The secret goes to the macOS keychain.
2. Connect channel: sign in with a test user, choose the channel and allow every permission.
3. Set the channel defaults: privacy, made for kids, category, language.

## Create the first Kutty Stories automation

1. Automations, New. Pick the Kutty Stories pipeline (it appears in the list once installed).
2. Content: the form comes from the pipeline's settings, with a default for every field.
3. Languages: for example English and Tamil.
4. Targets: one row per channel and language, with the video variants to publish.
5. Schedule: manual, every N hours, or a cron expression in your time zone.
6. Review: always (the default), or auto-approve when the quality score reaches a threshold.
7. Save, then Run now and follow the stages live on the run page.

## Review and publishing

- Uploads are **private** and every run **waits for your review** unless an automation says
  otherwise. Approve or reject on the run page, then publish.
- Kids' content is always marked **made for kids**: a pipeline that makes kids' content forces it
  on for every target, whatever the channel default.
- A target may set a publish delay: the video uploads private and YouTube makes it public later.
- Tamil text written by the AI (titles, descriptions, narration, subtitles) needs a read by a
  native speaker before you publish.

## Where files live

Everything is under the data directory, `~/.yt-automator` by default (`AUTOMATOR_DATA_DIR`):

| Path | Contents |
| --- | --- |
| `automator.db` | SQLite database: credentials, channels, automations, runs |
| `runs/<run id>/` | every artifact of a run: video, subtitles, thumbnail, metadata |
| `assets/music/` | your CC0 tracks for the music library provider |
| `tools/ace-step/` | the ACE-Step virtual environment |
| `logs/` | service logs when the app runs under launchd |
| `secrets.enc`, `secrets.key` | encrypted secrets, only when no keychain is available |

OAuth tokens and API keys live in the macOS keychain, never in the repository, logs or API responses.

## Not yet verified on real hardware

The code paths below are tested with fakes only. Expect to adjust options the first time:

- mflux image generation
- DepthFlow motion
- edge-tts, Kokoro and Whisper alignment (mlx-whisper, faster-whisper)
- ACE-Step music
- live Groq, Gemini and Ollama calls
- real Google OAuth and YouTube upload
- `scripts/setup.sh` itself, including Pillow finding libraqm for Tamil text shaping

## Development

Commands run from the repository root: `just setup`, `just check` (exactly what CI runs), `just dev`.
Every change follows the plan, implement, audit, review, ship and compound loop in `CLAUDE.md`.
The layer rules are in `.claude/rules/architecture.md`; the contract is `docs/spec/platform.md`.

## Licence

MIT. See `LICENSE`.
