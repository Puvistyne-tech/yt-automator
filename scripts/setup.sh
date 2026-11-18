#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
WEB_DIR="$REPO_ROOT/web"
DATA_DIR="${AUTOMATOR_DATA_DIR:-$HOME/.yt-automator}"
APP_HOST="${AUTOMATOR_HOST:-127.0.0.1}"
APP_PORT="${AUTOMATOR_PORT:-8000}"
APP_URL="http://$APP_HOST:$APP_PORT"
REDIRECT_BASE_URL="${AUTOMATOR_REDIRECT_BASE_URL:-$APP_URL}"
PYTHON_VERSION="${SETUP_PYTHON_VERSION:-3.12}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma3:12b}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
OLLAMA_WAIT_SECONDS="${OLLAMA_WAIT_SECONDS:-30}"
ACE_STEP_PYTHON_VERSION="${ACE_STEP_PYTHON_VERSION:-3.11}"
ACE_STEP_SOURCE="${ACE_STEP_SOURCE:-git+https://github.com/ace-step/ACE-Step.git}"
ACE_STEP_DIR="$DATA_DIR/tools/ace-step"
MUSIC_DIR="$DATA_DIR/assets/music"
EXTRAS_FILE="$DATA_DIR/setup/extras"
LOG_DIR="$DATA_DIR/logs"
SERVICE_LABEL="com.yt-automator.app"
SERVICE_PLIST="$HOME/Library/LaunchAgents/$SERVICE_LABEL.plist"

DRY_RUN=0
WANT_BASE=1
WANT_OLLAMA=0
WANT_IMAGES=0
WANT_MOTION=0
WANT_SPEECH=0
WANT_MUSIC=0
WANT_FONTS=0
WANT_SERVICE=0
WANT_UNINSTALL_SERVICE=0
BASE_CHOSEN=0
INSTALLED=()
SKIPPED=()
NOTES=()
EXTRAS=()

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

usage() {
  cat <<USAGE
Usage: scripts/setup.sh [options]

Sets up YouTube Automator on an Apple-silicon Mac. Safe to run again.
With no option it installs the base: uv, just, ffmpeg, node, pnpm, the
backend and web dependencies, and the built UI.

  --ollama             Ollama and the $OLLAMA_MODEL model (set OLLAMA_MODEL to change)
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
  -h, --help           show this help
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

make_dir() {
  if [ -d "$1" ]; then
    skipped "$1"
    return 0
  fi
  run mkdir -p "$1"
  installed "$1"
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

brew_formula() {
  if have brew && brew list --formula "$1" >/dev/null 2>&1; then
    skipped "$1"
    return 0
  fi
  run brew install "$1"
  installed "$1"
}

brew_cask() {
  if have brew && brew list --cask "$1" >/dev/null 2>&1; then
    skipped "$1"
    return 0
  fi
  run brew install --cask "$1"
  installed "$1"
}

uv_tool() {
  local command_name="$1" package="$2"
  if have "$command_name"; then
    skipped "$command_name"
    return 0
  fi
  run uv tool install --python "$PYTHON_VERSION" "$package"
  installed "$package"
}

ensure_tool() {
  local command_name="$1" formula="$2"
  if have "$command_name"; then
    skipped "$command_name"
    return 0
  fi
  brew_formula "$formula"
}

ensure_pnpm() {
  if have pnpm; then
    skipped pnpm
  elif have corepack; then
    run corepack enable pnpm
    installed "pnpm (corepack)"
  else
    brew_formula pnpm
  fi
}

backend_python_version() {
  "$BACKEND_DIR/.venv/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true
}

ensure_backend_venv() {
  run uv python install "$PYTHON_VERSION"
  if [ "$(backend_python_version)" = "$PYTHON_VERSION" ]; then
    skipped "backend virtual environment (Python $PYTHON_VERSION)"
    return 0
  fi
  run_in "$BACKEND_DIR" uv sync --python "$PYTHON_VERSION"
  installed "backend virtual environment (Python $PYTHON_VERSION, needed by Kokoro)"
}

install_base() {
  section "base: uv, just, ffmpeg, node, pnpm, dependencies and the UI build"
  require_brew
  ensure_tool uv uv
  if have just; then skipped just; else run uv tool install rust-just && installed just; fi
  ensure_tool ffmpeg ffmpeg
  ensure_tool node node
  ensure_pnpm
  ensure_backend_venv
  run_in "$REPO_ROOT" just setup
  run_in "$WEB_DIR" pnpm build
  installed "backend and web dependencies, UI build in web/dist"
}

ollama_running() {
  curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1
}

wait_for_ollama() {
  local waited=0
  is_dry_run && return 0
  until ollama_running; do
    [ "$waited" -ge "$OLLAMA_WAIT_SECONDS" ] && fail "Ollama did not answer at $OLLAMA_URL"
    sleep 1
    waited=$((waited + 1))
  done
}

ollama_has_model() {
  have ollama && ollama_running && ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$OLLAMA_MODEL"
}

install_ollama() {
  section "ollama: local text model server and $OLLAMA_MODEL"
  require_brew
  brew_formula ollama
  if ollama_running; then skipped "ollama server"; else run brew services start ollama; fi
  wait_for_ollama
  if ollama_has_model; then
    skipped "$OLLAMA_MODEL"
  else
    run ollama pull "$OLLAMA_MODEL"
    installed "ollama model $OLLAMA_MODEL"
  fi
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
  EXTRAS+=(tts align mac)
  note "edge-tts uses Microsoft's online voices: free and no account, but it needs internet."
  note "Kokoro and Whisper models download from Hugging Face on first use: free, no account."
}

ace_step_ready() {
  [ -x "$ACE_STEP_DIR/bin/python" ] && "$ACE_STEP_DIR/bin/python" -c "import acestep" >/dev/null 2>&1
}

install_music() {
  section "music: ACE-Step in its own venv and the CC0 music folder"
  require_uv
  if ace_step_ready; then
    skipped "ACE-Step venv at $ACE_STEP_DIR"
  else
    [ -x "$ACE_STEP_DIR/bin/python" ] || run uv venv --python "$ACE_STEP_PYTHON_VERSION" "$ACE_STEP_DIR"
    run uv pip install --python "$ACE_STEP_DIR/bin/python" "$ACE_STEP_SOURCE"
    installed "ACE-Step venv at $ACE_STEP_DIR"
  fi
  make_dir "$MUSIC_DIR"
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
  for extra in tts align mac; do
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
    note "Pillow finds libraqm only with DYLD_FALLBACK_LIBRARY_PATH=$(brew --prefix)/lib. The service sets it; export it before just dev."
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

stop_service() {
  if is_dry_run; then
    say "    would run: launchctl bootout $(launchd_target)/$SERVICE_LABEL"
    return 0
  fi
  launchctl bootout "$(launchd_target)/$SERVICE_LABEL" >/dev/null 2>&1 || true
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
  if [ ! -f "$SERVICE_PLIST" ] && ! is_dry_run; then
    say "    no launchd agent at $SERVICE_PLIST"
    return 0
  fi
  stop_service
  run rm -f "$SERVICE_PLIST"
  installed "removed $SERVICE_PLIST"
}

print_list() {
  local title="$1"
  shift
  say "$title"
  if [ "$#" -eq 0 ]; then say "  nothing"; fi
  for item in "$@"; do say "  - $item"; done
}

print_summary() {
  section "summary"
  if is_dry_run; then say "Dry run: nothing was changed."; fi
  local done_title="Installed:"
  if is_dry_run; then done_title="Planned:"; fi
  print_list "$done_title" ${INSTALLED[@]+"${INSTALLED[@]}"}
  print_list "Skipped:" ${SKIPPED[@]+"${SKIPPED[@]}"}
  print_list "Notes:" ${NOTES[@]+"${NOTES[@]}"}
  say ""
  say "Next steps:"
  if [ "$WANT_SERVICE" = 1 ]; then
    say "  1. The app starts at login. Open $APP_URL"
  else
    say "  1. Start the app with: just dev-api   (or install it as a service with --service)"
    say "     then open $APP_URL"
  fi
  say "  2. Add API keys (Groq, Gemini, Hugging Face) under Providers > Secrets in the UI."
  say "  3. Check everything with: just doctor"
}

select_models() {
  WANT_OLLAMA=1
  WANT_IMAGES=1
  WANT_MOTION=1
  WANT_SPEECH=1
  WANT_MUSIC=1
  WANT_FONTS=1
}

parse_flag() {
  case "$1" in
    --ollama) WANT_OLLAMA=1 ;;
    --images) WANT_IMAGES=1 ;;
    --motion) WANT_MOTION=1 ;;
    --speech) WANT_SPEECH=1 ;;
    --music) WANT_MUSIC=1 ;;
    --fonts) WANT_FONTS=1 ;;
    --models) select_models ;;
    --service) WANT_SERVICE=1 ;;
    --uninstall-service) WANT_UNINSTALL_SERVICE=1 ;;
    --all) select_models && WANT_SERVICE=1 && BASE_CHOSEN=1 ;;
    --no-base) WANT_BASE=0 ;;
    --dry-run) DRY_RUN=1 ;;
    -h | --help) usage && exit 0 ;;
    *) usage >&2 && exit 2 ;;
  esac
}

only_uninstalling() {
  [ "$WANT_UNINSTALL_SERVICE" = 1 ] && [ "$BASE_CHOSEN" = 0 ] &&
    [ "$((WANT_OLLAMA + WANT_IMAGES + WANT_MOTION + WANT_SPEECH + WANT_MUSIC + WANT_FONTS + WANT_SERVICE))" = 0 ]
}

run_selected() {
  if [ "$WANT_BASE" = 1 ]; then install_base; fi
  if [ "$WANT_OLLAMA" = 1 ]; then install_ollama; fi
  if [ "$WANT_IMAGES" = 1 ]; then install_images; fi
  if [ "$WANT_MOTION" = 1 ]; then install_motion; fi
  if [ "$WANT_SPEECH" = 1 ]; then install_speech; fi
  if [ "$WANT_MUSIC" = 1 ]; then install_music; fi
  if [ "$WANT_FONTS" = 1 ]; then install_fonts; fi
  if [ "$WANT_BASE" = 1 ] || [ "${#EXTRAS[@]}" -gt 0 ]; then sync_extras; fi
  if [ "$WANT_FONTS" = 1 ]; then verify_raqm; fi
  if [ "$WANT_UNINSTALL_SERVICE" = 1 ]; then uninstall_service; fi
  if [ "$WANT_SERVICE" = 1 ]; then install_service; fi
}

main() {
  local flag
  for flag in "$@"; do parse_flag "$flag"; done
  if only_uninstalling; then WANT_BASE=0; fi
  check_platform
  say "YouTube Automator setup. Data directory: $DATA_DIR"
  run_selected
  print_summary
}

main "$@"
