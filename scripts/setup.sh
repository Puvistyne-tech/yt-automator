#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
WEB_DIR="$REPO_ROOT/web"
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
DATA_DIR="${AUTOMATOR_DATA_DIR:-$HOME/.yt-automator}"
APP_HOST="${AUTOMATOR_HOST:-127.0.0.1}"
APP_PORT="${AUTOMATOR_PORT:-8000}"
USER_REDIRECT_BASE_URL="${AUTOMATOR_REDIRECT_BASE_URL:-}"
PYTHON_VERSION="${SETUP_PYTHON_VERSION:-3.12}"
USER_OLLAMA_MODEL="${OLLAMA_MODEL:-}"
USER_OLLAMA_URL="${OLLAMA_URL:-}"
OLLAMA_MODEL="${USER_OLLAMA_MODEL:-gemma3:12b}"
OLLAMA_URL="${USER_OLLAMA_URL:-http://127.0.0.1:11434}"
OLLAMA_WAIT_SECONDS="${OLLAMA_WAIT_SECONDS:-30}"
SERVICE_STOP_WAIT_SECONDS="${SERVICE_STOP_WAIT_SECONDS:-15}"
ACE_STEP_PYTHON_VERSION="${ACE_STEP_PYTHON_VERSION:-3.11}"
ACE_STEP_SOURCE="${ACE_STEP_SOURCE:-git+https://github.com/ace-step/ACE-Step.git}"
ACE_STEP_DIR="$DATA_DIR/tools/ace-step"
MUSIC_DIR="$DATA_DIR/assets/music"
SERVICE_LABEL="com.yt-automator.app"
SERVICE_PLIST="$HOME/Library/LaunchAgents/$SERVICE_LABEL.plist"
SETUP_EXTRA_PATH="${SETUP_EXTRA_PATH-$HOME/.local/bin:/opt/homebrew/bin}"
MODEL_GROUPS=(ollama images motion speech music fonts)
PYTHON_EXTRAS=(tts align mac)

DRY_RUN=0
NO_BASE=0
SELECTED=" "
INSTALLED=()
SKIPPED=()
NOTES=()
EXTRAS=()

if [ -n "$SETUP_EXTRA_PATH" ]; then export PATH="$SETUP_EXTRA_PATH:$PATH"; fi

usage() {
  cat <<USAGE
Usage: scripts/setup.sh [options]

Sets up YouTube Automator on an Apple-silicon Mac. Safe to run again.
With no option it installs the base: uv, just, ffmpeg, node, pnpm, the
backend and web dependencies, and the built UI.

  --ollama             Ollama and the app's default model ($OLLAMA_MODEL)
  --images             mflux (FLUX image models on Apple silicon)
  --motion             DepthFlow parallax motion
  --speech             edge-tts, Kokoro, espeak-ng and Whisper alignment
  --music              ACE-Step in its own venv and the CC0 music folder
  --fonts              Noto Sans, Noto Sans Tamil and libraqm
  --models             all of the model groups above
  --service            start the app at login with a launchd agent
  --uninstall-service  remove the launchd agent
  --all                base, every model group and the service
  --no-base            skip the base step
  --dry-run            print the plan without changing anything
  --print-defaults     print the script's built-in defaults as KEY=value
  -h, --help           show this help

Environment: AUTOMATOR_DATA_DIR, AUTOMATOR_HOST, AUTOMATOR_PORT and
AUTOMATOR_REDIRECT_BASE_URL as for the app. OLLAMA_MODEL pulls another model;
choose it afterwards in the Ollama provider's Model option under Providers.
SETUP_EXTRA_PATH is prepended to PATH (default ~/.local/bin:/opt/homebrew/bin).
USAGE
}

say() {
  printf '%s\n' "$*"
}

section() {
  printf '\n==> %s\n' "$*"
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

is_dry_run() {
  [ "$DRY_RUN" = 1 ]
}

installed() {
  INSTALLED+=("$1")
}

skipped() {
  SKIPPED+=("$1 (already present)")
  say "    $1 is already present"
}

note() {
  NOTES+=("$1")
  say "    note: $1"
}

run() {
  if is_dry_run; then
    say "    would run: $*"
    return 0
  fi
  say "    \$ $*"
  "$@"
}

run_in() {
  local folder="$1"
  shift
  if is_dry_run; then
    say "    would run in $folder: $*"
    return 0
  fi
  say "    \$ (cd $folder && $*)"
  (cd "$folder" && "$@")
}

ensure() {
  local label="$1" check="$2" subject="$3"
  shift 3
  if "$check" "$subject"; then
    skipped "$label"
    return 0
  fi
  "$@"
  installed "$label"
}

wait_for() {
  local check="$1" limit="$2" message="$3" waited=0
  is_dry_run && return 0
  until "$check"; do
    [ "$waited" -ge "$limit" ] && fail "$message"
    sleep 1
    waited=$((waited + 1))
  done
}

brew_has_formula() {
  have brew && brew list --formula "$1" >/dev/null 2>&1
}

brew_has_cask() {
  have brew && brew list --cask "$1" >/dev/null 2>&1
}

brew_formula() {
  ensure "$1" brew_has_formula "$1" run brew install "$1"
}

brew_cask() {
  ensure "$1" brew_has_cask "$1" run brew install --cask "$1"
}

uv_tool() {
  ensure "$2" have "$1" run uv tool install --python "$PYTHON_VERSION" "$2"
}

derive_settings() {
  APP_URL="http://$APP_HOST:$APP_PORT"
  REDIRECT_BASE_URL="${USER_REDIRECT_BASE_URL:-http://127.0.0.1:$APP_PORT}"
  EXTRAS_FILE="$DATA_DIR/setup/extras"
  LOG_DIR="$DATA_DIR/logs"
}

print_defaults() {
  say "DATA_DIR=$DATA_DIR"
  say "APP_HOST=$APP_HOST"
  say "APP_PORT=$APP_PORT"
  say "OLLAMA_MODEL=$OLLAMA_MODEL"
  say "OLLAMA_URL=$OLLAMA_URL"
  say "ACE_STEP_DIR=$ACE_STEP_DIR"
  say "MUSIC_DIR=$MUSIC_DIR"
}

apply_default() {
  case "$1" in
    DATA_DIR) DATA_DIR="$2" ;;
    APP_HOST) APP_HOST="$2" ;;
    APP_PORT) APP_PORT="$2" ;;
    OLLAMA_MODEL) OLLAMA_MODEL="${USER_OLLAMA_MODEL:-$2}" ;;
    OLLAMA_URL) OLLAMA_URL="${USER_OLLAMA_URL:-$2}" ;;
    ACE_STEP_DIR) ACE_STEP_DIR="$2" ;;
    MUSIC_DIR) MUSIC_DIR="$2" ;;
  esac
}

load_app_defaults() {
  local key value
  [ -x "$BACKEND_PYTHON" ] || return 0
  while IFS='=' read -r key value; do
    apply_default "$key" "$value"
  done < <("$BACKEND_PYTHON" -m automator.doctor --print-defaults 2>/dev/null || true)
  derive_settings
}

check_platform() {
  local system machine
  system="$(uname -s)"
  machine="$(uname -m)"
  if [ "$system" = "Darwin" ] && [ "$machine" = "arm64" ]; then
    return 0
  fi
  if is_dry_run; then
    say "This host is $system $machine. The plan below targets macOS on Apple silicon."
    return 0
  fi
  fail "scripts/setup.sh supports macOS on Apple silicon only (this host is $system $machine)"
}

require_brew() {
  if have brew; then
    return 0
  fi
  if is_dry_run; then
    say "    Homebrew is missing: the real run stops here until it is installed"
    return 0
  fi
  fail "Homebrew is required. Install it for free from https://brew.sh, then run this again."
}

require_uv() {
  have uv || is_dry_run || fail "uv is missing: run scripts/setup.sh without --no-base first"
}

ensure_pnpm() {
  if have pnpm || ! have corepack; then
    ensure pnpm have pnpm run brew install pnpm
  else
    run corepack enable pnpm
    installed "pnpm (corepack)"
  fi
}

backend_python_version() {
  "$BACKEND_PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true
}

backend_venv_ready() {
  [ "$(backend_python_version)" = "$1" ]
}

install_base() {
  section "base: uv, just, ffmpeg, node, pnpm, dependencies and the UI build"
  require_brew
  ensure uv have uv run brew install uv
  ensure just have just run uv tool install rust-just
  run uv tool update-shell
  note "Open a new terminal afterwards so ~/.local/bin (just, mflux-generate, depthflow) is on PATH."
  ensure ffmpeg have ffmpeg run brew install ffmpeg
  ensure node have node run brew install node
  ensure_pnpm
  run uv python install "$PYTHON_VERSION"
  ensure "backend venv (Python $PYTHON_VERSION, needed by Kokoro)" backend_venv_ready "$PYTHON_VERSION" \
    run_in "$BACKEND_DIR" uv sync --python "$PYTHON_VERSION"
  run_in "$REPO_ROOT" just setup
  run_in "$WEB_DIR" pnpm build
  installed "backend and web dependencies, UI build in web/dist"
}

ollama_running() {
  curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1
}

ollama_has_model() {
  have ollama && ollama_running && ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$1"
}

install_ollama() {
  section "ollama: local text model server and $OLLAMA_MODEL"
  require_brew
  brew_formula ollama
  ensure "ollama server" ollama_running "" run brew services start ollama
  wait_for ollama_running "$OLLAMA_WAIT_SECONDS" "Ollama did not answer at $OLLAMA_URL"
  ensure "ollama model $OLLAMA_MODEL" ollama_has_model "$OLLAMA_MODEL" run ollama pull "$OLLAMA_MODEL"
  note "Ollama models are free downloads with no account. $OLLAMA_MODEL is several GB."
}

install_images() {
  section "images: mflux, FLUX image models running on Apple silicon"
  require_uv
  uv_tool mflux-generate mflux
  note "FLUX schnell weights download from Hugging Face on first use: free, no account, tens of GB."
  note "FLUX dev is gated: accept its licence on huggingface.co and add a read token as the huggingface_token secret in the UI."
}

install_motion() {
  section "motion: DepthFlow parallax"
  require_uv
  uv_tool depthflow depthflow
  note "DepthFlow is AGPL and runs as a separate program. Its depth model downloads on first use."
}

install_speech() {
  section "speech: edge-tts, Kokoro, espeak-ng and Whisper alignment"
  require_brew
  brew_formula espeak-ng
  EXTRAS+=("${PYTHON_EXTRAS[@]}")
  note "edge-tts uses Microsoft's online voices: free and no account, but it needs internet."
  note "Kokoro and Whisper models download from Hugging Face on first use: free, no account."
}

ace_step_ready() {
  [ -x "$1/bin/python" ] && "$1/bin/python" -c "import acestep" >/dev/null 2>&1
}

install_ace_step() {
  [ -x "$ACE_STEP_DIR/bin/python" ] || run uv venv --python "$ACE_STEP_PYTHON_VERSION" "$ACE_STEP_DIR"
  run uv pip install --python "$ACE_STEP_DIR/bin/python" "$ACE_STEP_SOURCE"
}

is_dir() {
  [ -d "$1" ]
}

install_music() {
  section "music: ACE-Step in its own venv and the CC0 music folder"
  require_uv
  ensure "ACE-Step venv at $ACE_STEP_DIR" ace_step_ready "$ACE_STEP_DIR" install_ace_step
  ensure "$MUSIC_DIR" is_dir "$MUSIC_DIR" run mkdir -p "$MUSIC_DIR"
  note "ACE-Step checkpoints download from Hugging Face on first use: free, no account, several GB."
  note "Put your own CC0 tracks in $MUSIC_DIR for the music library provider."
}

install_fonts() {
  section "fonts: Noto Sans, Noto Sans Tamil and libraqm"
  require_brew
  brew_formula libraqm
  brew_cask font-noto-sans
  brew_cask font-noto-sans-tamil
}

saved_extras() {
  [ -f "$EXTRAS_FILE" ] || return 0
  cat "$EXTRAS_FILE"
}

wanted_extras() {
  {
    saved_extras
    if [ "${#EXTRAS[@]}" -gt 0 ]; then printf '%s\n' "${EXTRAS[@]}"; fi
  } | awk 'NF' | sort -u
}

sync_extras() {
  local extras extra args=()
  extras="$(wanted_extras)"
  [ -n "$extras" ] || return 0
  section "python extras: $(printf '%s' "$extras" | tr '\n' ' ')"
  for extra in "${PYTHON_EXTRAS[@]}"; do
    if printf '%s\n' "$extras" | grep -qx "$extra"; then args+=(--extra "$extra"); fi
  done
  run_in "$BACKEND_DIR" uv sync --python "$PYTHON_VERSION" ${args[@]+"${args[@]}"}
  run mkdir -p "$(dirname "$EXTRAS_FILE")"
  is_dry_run || printf '%s\n' "$extras" >"$EXTRAS_FILE"
  installed "Python extras: $(printf '%s' "$extras" | tr '\n' ' ')"
}

raqm_check() {
  (cd "$BACKEND_DIR" && uv run python -c 'from PIL import features; raise SystemExit(not features.check("raqm"))') >/dev/null 2>&1
}

verify_raqm() {
  if is_dry_run; then
    say "    would check that Pillow finds libraqm for Tamil text shaping"
  elif raqm_check; then
    say "    Pillow finds libraqm: Tamil text shaping works"
  elif DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib" raqm_check; then
    note "Pillow finds libraqm only with DYLD_FALLBACK_LIBRARY_PATH=$(brew --prefix)/lib. The service, just dev-api and just doctor set it."
  else
    note "Pillow cannot find libraqm: Tamil titles on thumbnails may render with broken letters."
  fi
}

service_plist() {
  local uv_bin brew_prefix
  uv_bin="$(command -v uv || printf 'uv')"
  brew_prefix="$(brew --prefix 2>/dev/null || printf '/opt/homebrew')"
  cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$SERVICE_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$uv_bin</string><string>run</string><string>--project</string><string>$BACKEND_DIR</string>
    <string>python</string><string>-m</string><string>automator.main</string>
  </array>
  <key>WorkingDirectory</key><string>$BACKEND_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:$brew_prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>DYLD_FALLBACK_LIBRARY_PATH</key><string>$brew_prefix/lib</string>
    <key>AUTOMATOR_HOST</key><string>$APP_HOST</string>
    <key>AUTOMATOR_PORT</key><string>$APP_PORT</string>
    <key>AUTOMATOR_DATA_DIR</key><string>$DATA_DIR</string>
    <key>AUTOMATOR_REDIRECT_BASE_URL</key><string>$REDIRECT_BASE_URL</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardOutPath</key><string>$LOG_DIR/service.out.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/service.err.log</string>
</dict>
</plist>
PLIST
}

launchd_target() {
  printf 'gui/%s' "$(id -u)"
}

service_stopped() {
  ! launchctl print "$(launchd_target)/$SERVICE_LABEL" >/dev/null 2>&1
}

stop_service() {
  if is_dry_run; then
    say "    would run: launchctl bootout $(launchd_target)/$SERVICE_LABEL"
    return 0
  fi
  launchctl bootout "$(launchd_target)/$SERVICE_LABEL" >/dev/null 2>&1 || true
  wait_for service_stopped "$SERVICE_STOP_WAIT_SECONDS" "launchd did not stop $SERVICE_LABEL"
}

install_service() {
  section "service: launchd agent $SERVICE_LABEL on $APP_URL"
  run mkdir -p "$(dirname "$SERVICE_PLIST")" "$LOG_DIR"
  if is_dry_run; then
    say "    would write $SERVICE_PLIST with AUTOMATOR_HOST=$APP_HOST AUTOMATOR_PORT=$APP_PORT"
  else
    service_plist >"$SERVICE_PLIST"
  fi
  stop_service
  run launchctl bootstrap "$(launchd_target)" "$SERVICE_PLIST"
  installed "launchd agent $SERVICE_PLIST (logs in $LOG_DIR)"
}

uninstall_service() {
  section "uninstall service: launchd agent $SERVICE_LABEL"
  stop_service
  if [ ! -f "$SERVICE_PLIST" ] && ! is_dry_run; then
    say "    no launchd agent file at $SERVICE_PLIST"
    return 0
  fi
  run rm -f "$SERVICE_PLIST"
  installed "removed $SERVICE_PLIST"
}

print_list() {
  local title="$1" item
  shift
  say "$title"
  if [ "$#" -eq 0 ]; then say "  nothing"; fi
  for item in "$@"; do say "  - $item"; done
}

print_next_steps() {
  say ""
  say "Next steps:"
  if wants service; then
    say "  1. The app starts at login. Open $APP_URL"
  else
    say "  1. Start the app with: just dev-api   (or install it as a service with --service)"
    say "     then open $APP_URL"
  fi
  say "  2. Add API keys (Groq, Gemini, Hugging Face) under Providers > Secrets in the UI."
  say "  3. Check everything with: just doctor"
}

print_summary() {
  local done_title="Installed:"
  section "summary"
  if is_dry_run; then
    say "Dry run: nothing was changed."
    done_title="Planned:"
  fi
  print_list "$done_title" ${INSTALLED[@]+"${INSTALLED[@]}"}
  print_list "Skipped:" ${SKIPPED[@]+"${SKIPPED[@]}"}
  print_list "Notes:" ${NOTES[@]+"${NOTES[@]}"}
  print_next_steps
}

select_group() {
  SELECTED="$SELECTED$1 "
}

wants() {
  case "$SELECTED" in *" $1 "*) return 0 ;; esac
  return 1
}

select_models() {
  local group
  for group in "${MODEL_GROUPS[@]}"; do select_group "$group"; done
}

parse_flag() {
  case "$1" in
    --ollama | --images | --motion | --speech | --music | --fonts | --service | --uninstall-service)
      select_group "${1#--}" ;;
    --models) select_models ;;
    --all) select_models && select_group service ;;
    --no-base) NO_BASE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --print-defaults) print_defaults && exit 0 ;;
    -h | --help) usage && exit 0 ;;
    *) usage >&2 && exit 2 ;;
  esac
}

choose_base() {
  if [ "$NO_BASE" = 1 ] || [ "$SELECTED" = " uninstall-service " ]; then return 0; fi
  wants base || select_group base
}

run_selected() {
  local group
  if wants base; then install_base; fi
  load_app_defaults
  for group in "${MODEL_GROUPS[@]}"; do
    if wants "$group"; then "install_$group"; fi
  done
  if wants base || [ "${#EXTRAS[@]}" -gt 0 ]; then sync_extras; fi
  if wants fonts; then verify_raqm; fi
  if wants uninstall-service; then uninstall_service; fi
  if wants service; then install_service; fi
}

main() {
  local flag
  derive_settings
  for flag in "$@"; do parse_flag "$flag"; done
  choose_base
  check_platform
  say "YouTube Automator setup. Data directory: $DATA_DIR"
  run_selected
  print_summary
}

main "$@"
