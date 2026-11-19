#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
WEB_DIR="$REPO_ROOT/web"
BACKEND_PYTHON="${SETUP_BACKEND_PYTHON:-$BACKEND_DIR/.venv/bin/python}"
DATA_DIR="${AUTOTUBE_DATA_DIR:-$HOME/.autotube}"
APP_HOST="${AUTOTUBE_HOST:-127.0.0.1}"
APP_PORT="${AUTOTUBE_PORT:-8000}"
USER_REDIRECT_BASE_URL="${AUTOTUBE_REDIRECT_BASE_URL:-}"
APP_REDIRECT_BASE_URL=""
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
SERVICE_LABEL="com.autotube.app"
SERVICE_PLIST="$HOME/Library/LaunchAgents/$SERVICE_LABEL.plist"
SETUP_EXTRA_PATH="${SETUP_EXTRA_PATH-$HOME/.local/bin:/opt/homebrew/bin}"
MODEL_GROUPS=(ollama images motion speech music fonts video voices)
PYTHON_EXTRAS=(tts align mac)
MLX_AUDIO_PACKAGE="${MLX_AUDIO_PACKAGE:-mlx-audio==0.6.6}"
LTX_MLX_SOURCE="${LTX_MLX_SOURCE:-https://github.com/dgrauet/ltx-2-mlx}"
LTX_MODEL_REPO="${LTX_MODEL_REPO:-reverie-studio/ltx-2.5-mlx-q4-distilled}"
MODELS_FROM="${AUTOTUBE_MODELS_FROM:-}"
LTX_PACKAGES=(ltx-core-mlx ltx-pipelines-mlx)
FLUX_KLEIN_REPO="black-forest-labs/FLUX.2-klein-4B"
FFMPEG_FORMULA="ffmpeg-full"
SVARA_REPO="mlx-community/svara-tts-v1-4bit"
VOICE_MODELS=(
  mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit
  mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit
  mlx-community/chatterbox-turbo-4bit
  aruntemme/maya2-native-mlx-8bit
  "$SVARA_REPO"
  mlx-community/whisper-large-v3-turbo
)
VOICE_CACHE_REPOS=(
  mlx-community/S3TokenizerV2
  kyutai/moshiko-pytorch-bf16
  aufklarer/SpeechBrain-ECAPA-VoxCeleb-20M-MLX
  mlx-community/snac_24khz
)
MLX_DONE=" "

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

Sets up AutoTube on an Apple-silicon Mac. Safe to run again.
With no option it installs the base: uv, just, ffmpeg, node, pnpm, the
backend and web dependencies, and the built UI. ffmpeg comes from
Homebrew's keg-only ffmpeg-full, which has libass for burned-in subtitles.

  --ollama             Ollama and the app's default model ($OLLAMA_MODEL)
  --images             mflux and the FLUX.2 klein 4B weights (about 16 GB)
  --motion             DepthFlow parallax motion
  --speech             edge-tts, Kokoro, espeak-ng and Whisper alignment
  --music              ACE-Step in its own venv and the CC0 music folder
  --fonts              Noto Sans, Noto Sans Tamil and libraqm
  --video              LTX-2.5 image-to-video (ltx-2-mlx) and its weights
  --voices             mlx-audio voices, mlx-whisper and their weights
  --models             all of the model groups above
  --service            start the app at login with a launchd agent
  --uninstall-service  remove the launchd agent
  --all                base, every model group and the service
  --no-base            skip the base step
  --dry-run            print the plan without changing anything
  --print-defaults     print the script's built-in defaults as KEY=value
  -h, --help           show this help

Environment: AUTOTUBE_DATA_DIR, AUTOTUBE_HOST, AUTOTUBE_PORT and
AUTOTUBE_REDIRECT_BASE_URL as for the app. OLLAMA_MODEL pulls another model;
choose it afterwards in the Ollama provider's Model option under Providers.
SETUP_EXTRA_PATH is prepended to PATH (default ~/.local/bin:/opt/homebrew/bin).
SETUP_BACKEND_PYTHON is the backend venv Python asked for the app's defaults
(default backend/.venv/bin/python). OLLAMA_WAIT_SECONDS and
SERVICE_STOP_WAIT_SECONDS are whole numbers of seconds.
--images, --video and --voices share the venv <data dir>/venvs/mlx and put weights in
<data dir>/models with the Hugging Face cache in <data dir>/hf.
AUTOTUBE_MODELS_FROM links weights from <folder>/local/<owner>__<repo> and the
cache from <folder>/hf instead of downloading. MLX_AUDIO_PACKAGE (default
mlx-audio==0.6.6), LTX_MLX_SOURCE and LTX_MODEL_REPO override what is installed.
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
    if ! [ "$waited" -lt "$limit" ] 2>/dev/null; then fail "$message"; fi
    sleep 1
    waited=$((waited + 1))
  done
}

require_seconds() {
  case "$2" in
    '' | *[!0-9]*) fail "$1 must be a whole number of seconds, got '$2'" ;;
  esac
}

brew_has_formula() {
  have brew && brew list --formula "$1" >/dev/null 2>&1
}

brew_has_cask() {
  have brew && brew list --cask "$1" >/dev/null 2>&1
}

homebrew_prefix() {
  brew --prefix 2>/dev/null || printf '/opt/homebrew'
}

ffmpeg_full_bin() {
  printf '%s/opt/%s/bin' "$(homebrew_prefix)" "$FFMPEG_FORMULA"
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
  REDIRECT_BASE_URL="${USER_REDIRECT_BASE_URL:-${APP_REDIRECT_BASE_URL:-$(fallback_redirect_base)}}"
  EXTRAS_FILE="$DATA_DIR/setup/extras"
  LOG_DIR="$DATA_DIR/logs"
}

fallback_redirect_base() {
  case "$APP_HOST" in
    '' | 0.0.0.0 | ::) printf 'http://127.0.0.1:%s' "$APP_PORT" ;;
    *) printf 'http://%s:%s' "$APP_HOST" "$APP_PORT" ;;
  esac
}

print_defaults() {
  say "DATA_DIR=$DATA_DIR"
  say "APP_HOST=$APP_HOST"
  say "APP_PORT=$APP_PORT"
  say "REDIRECT_BASE_URL=$REDIRECT_BASE_URL"
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
    REDIRECT_BASE_URL) APP_REDIRECT_BASE_URL="$2" ;;
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
  done < <("$BACKEND_PYTHON" -m autotube.doctor --print-defaults 2>/dev/null || true)
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
  section "base: uv, just, ffmpeg-full, node, pnpm, dependencies and the UI build"
  require_brew
  ensure uv have uv run brew install uv
  ensure just have just run uv tool install rust-just
  run uv tool update-shell
  note "Open a new terminal afterwards so ~/.local/bin (just, mflux-generate, depthflow) is on PATH."
  brew_formula "$FFMPEG_FORMULA"
  note "$FFMPEG_FORMULA is keg-only: the service, just dev-api and just doctor put $(ffmpeg_full_bin) first on PATH."
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
  section "images: mflux and FLUX.2 klein 4B on Apple silicon"
  require_uv
  uv_tool mflux-generate mflux
  mlx_paths
  once ensure_mlx_venv
  once ensure_model_storage
  fetch_model "$FLUX_KLEIN_REPO"
  note "The FLUX.2 klein 4B weights are roughly 16 GB."
  once hf_login_note
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

venv_imports() {
  local python="$1" modules
  shift
  modules="$(IFS=,; printf '%s' "$*")"
  [ -x "$python" ] && "$python" -c "import $modules" >/dev/null 2>&1
}

install_into_venv() {
  local folder="$1" version="$2"
  shift 2
  [ -x "$folder/bin/python" ] || run uv venv --python "$version" "$folder"
  run uv pip install --python "$folder/bin/python" "$@"
}

ace_step_ready() {
  venv_imports "$1/bin/python" acestep
}

is_dir() {
  [ -d "$1" ]
}

install_music() {
  section "music: ACE-Step in its own venv and the CC0 music folder"
  require_uv
  ensure "ACE-Step venv at $ACE_STEP_DIR" ace_step_ready "$ACE_STEP_DIR" \
    install_into_venv "$ACE_STEP_DIR" "$ACE_STEP_PYTHON_VERSION" "$ACE_STEP_SOURCE"
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

mlx_paths() {
  MLX_VENV="$DATA_DIR/venvs/mlx"
  MLX_PYTHON="$MLX_VENV/bin/python"
  MLX_HF="$MLX_VENV/bin/hf"
  MODELS_DIR="$DATA_DIR/models"
  HF_DIR="$DATA_DIR/hf"
  LTX_CLONE="$DATA_DIR/tools/ltx-2-mlx"
  LTX_LINK="$HOME/.local/bin/ltx-2-mlx"
}

model_folder() {
  printf '%s' "${1/\//__}"
}

mlx_venv_ready() {
  venv_imports "$1" mlx_audio mlx_whisper huggingface_hub
}

once() {
  case "$MLX_DONE" in *" $1 "*) return 0 ;; esac
  MLX_DONE="$MLX_DONE$1 "
  "$@"
}

ensure_mlx_venv() {
  require_uv
  ensure "mlx venv at $MLX_VENV" mlx_venv_ready "$MLX_PYTHON" \
    install_into_venv "$MLX_VENV" "$PYTHON_VERSION" "$MLX_AUDIO_PACKAGE" mlx-whisper "huggingface_hub[cli]"
}

link_shared_cache() {
  if [ -n "$MODELS_FROM" ] && [ -d "$MODELS_FROM/hf" ] && [ ! -e "$HF_DIR" ]; then
    run ln -s "$MODELS_FROM/hf" "$HF_DIR"
    installed "Hugging Face cache $HF_DIR linked to $MODELS_FROM/hf"
  fi
}

ensure_model_storage() {
  run mkdir -p "$MODELS_DIR"
  link_shared_cache
}

place_model() {
  local repo="$1" target="$2" source
  source="$MODELS_FROM/local/$(model_folder "$repo")"
  if [ -n "$MODELS_FROM" ] && [ -d "$source" ]; then
    run ln -s "$source" "$target"
    return 0
  fi
  run env HF_HOME="$HF_DIR" "$MLX_HF" download "$repo" --local-dir "$target"
}

fetch_model() {
  local target
  target="$MODELS_DIR/$(model_folder "$1")"
  ensure "model $1" is_dir "$target" place_model "$1" "$target"
}

hf_cached() {
  [ -d "$HF_DIR/hub/models--${1/\//--}" ]
}

cache_repo() {
  ensure "cached repo $1" hf_cached "$1" run env HF_HOME="$HF_DIR" "$MLX_HF" download "$1"
}

ltx_ready() {
  [ -x "$1" ]
}

install_ltx() {
  local package args=()
  if [ ! -d "$LTX_CLONE/.git" ]; then
    run mkdir -p "$(dirname "$LTX_CLONE")"
    run git clone "$LTX_MLX_SOURCE" "$LTX_CLONE"
  fi
  for package in "${LTX_PACKAGES[@]}"; do args+=(-e "$LTX_CLONE/packages/$package"); done
  run uv pip install --python "$MLX_PYTHON" "${args[@]}"
}

link_ltx() {
  run mkdir -p "$(dirname "$LTX_LINK")"
  run ln -sf "$MLX_VENV/bin/ltx-2-mlx" "$LTX_LINK"
}

fix_svara_tokenizer() {
  local folder
  folder="$MODELS_DIR/$(model_folder "$SVARA_REPO")"
  if is_dry_run; then
    say "    would set tokenizer_name in $folder/config.json to $folder"
    return 0
  fi
  if [ ! -f "$folder/config.json" ]; then
    note "No config.json in $folder: the Svara tokenizer fix was skipped."
    return 0
  fi
  "$MLX_PYTHON" - "$folder" <<'PY'
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1])
config = folder / "config.json"
data = json.loads(config.read_text(encoding="utf-8"))
data["tokenizer_name"] = str(folder)
config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
  say "    tokenizer_name in $folder/config.json points at $folder"
}

hf_login_note() {
  note "If a download is refused, log in with: HF_HOME=$HF_DIR $MLX_HF auth login, and accept the terms on the model page."
  note "Set AUTOTUBE_MODELS_FROM to a folder with local/<owner>__<repo> and hf/ to reuse weights instead of downloading."
}

install_video() {
  section "video: LTX-2.5 image-to-video with ltx-2-mlx"
  mlx_paths
  once ensure_mlx_venv
  require_git
  ensure "ltx-2-mlx in $MLX_VENV" ltx_ready "$MLX_VENV/bin/ltx-2-mlx" install_ltx
  ensure "$LTX_LINK" ltx_ready "$LTX_LINK" link_ltx
  once ensure_model_storage
  fetch_model "$LTX_MODEL_REPO"
  note "The LTX-2.5 q4 weights are about 20 GB."
  once hf_login_note
}

install_voices() {
  local repo
  section "voices: mlx-audio voices and Whisper alignment"
  mlx_paths
  once ensure_mlx_venv
  once ensure_model_storage
  for repo in "${VOICE_MODELS[@]}"; do fetch_model "$repo"; done
  for repo in "${VOICE_CACHE_REPOS[@]}"; do cache_repo "$repo"; done
  fix_svara_tokenizer
  note "The voice models are about 15 GB in total."
  once hf_login_note
}

require_git() {
  have git || is_dry_run || fail "git is missing: install the Xcode command line tools with xcode-select --install"
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
  brew_prefix="$(homebrew_prefix)"
  cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$SERVICE_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$uv_bin</string><string>run</string><string>--project</string><string>$BACKEND_DIR</string>
    <string>python</string><string>-m</string><string>autotube.main</string>
  </array>
  <key>WorkingDirectory</key><string>$BACKEND_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$(ffmpeg_full_bin):$HOME/.local/bin:$brew_prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>DYLD_FALLBACK_LIBRARY_PATH</key><string>$brew_prefix/lib</string>
    <key>AUTOTUBE_HOST</key><string>$APP_HOST</string>
    <key>AUTOTUBE_PORT</key><string>$APP_PORT</string>
    <key>AUTOTUBE_DATA_DIR</key><string>$DATA_DIR</string>
    <key>AUTOTUBE_REDIRECT_BASE_URL</key><string>$REDIRECT_BASE_URL</string>
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
    say "    would write $SERVICE_PLIST with AUTOTUBE_HOST=$APP_HOST AUTOTUBE_PORT=$APP_PORT"
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
    --ollama | --images | --motion | --speech | --music | --fonts | --video | --voices | --service | --uninstall-service)
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
  require_seconds OLLAMA_WAIT_SECONDS "$OLLAMA_WAIT_SECONDS"
  require_seconds SERVICE_STOP_WAIT_SECONDS "$SERVICE_STOP_WAIT_SECONDS"
  derive_settings
  for flag in "$@"; do parse_flag "$flag"; done
  choose_base
  check_platform
  say "AutoTube setup. Data directory: $DATA_DIR"
  run_selected
  print_summary
}

main "$@"
