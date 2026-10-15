#!/usr/bin/env bash
# Launch with mandatory filesystem and network isolation.
set -euo pipefail
APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON="$APP_DIR/.venv/bin/python"
show_error() {
  printf '%s\n' "$1" >&2
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="Folio" --width=520 --text="$1" || true
  fi
}
if [[ ! -x "$PYTHON" ]]; then
  show_error "Folio ist nicht installiert. Bitte zuerst ./install.sh ausführen."
  exit 1
fi
if ! command -v bwrap >/dev/null 2>&1; then
  show_error "Bubblewrap (bwrap) fehlt. Aus Sicherheitsgründen wird Folio nicht ohne Sandbox gestartet."
  exit 1
fi
if [[ $# -gt 1 ]]; then
  echo "Verwendung: folio [Stammverzeichnis]" >&2
  exit 2
fi
if [[ $# -eq 0 ]]; then
  if ! ROOT="$($PYTHON "$APP_DIR/main.py" --choose)"; then
    # A cancelled folder dialog exits with code 2; no application window is expected.
    exit 0
  fi
else
  ROOT="$1"
fi
if [[ -z "$ROOT" || ! -d "$ROOT" ]]; then
  show_error "Stammverzeichnis existiert nicht: $ROOT"
  exit 2
fi
ROOT="$(realpath -e -- "$ROOT")"
[[ -d "$ROOT" ]] || exit 2

UID_NUM="$(id -u)"
ARGS=(
  --unshare-all
  --die-with-parent --new-session
  --ro-bind /usr /usr
  --ro-bind /etc /etc
  --symlink usr/bin /bin
  --symlink usr/sbin /sbin
  --symlink usr/lib /lib
  --symlink usr/lib64 /lib64
  --ro-bind "$APP_DIR" /app
  --ro-bind "$ROOT" /documents
  --proc /proc --dev /dev
  --tmpfs /tmp --dir /tmp/home
  --dir /run --dir /run/user --dir "/run/user/$UID_NUM"
  --setenv HOME /tmp/home
  --setenv XDG_CONFIG_HOME /tmp/home/.config
  --setenv XDG_CACHE_HOME /tmp/home/.cache
  --setenv XDG_DATA_HOME /tmp/home/.local/share
  --setenv XDG_RUNTIME_DIR "/run/user/$UID_NUM"
  --setenv PYTHONDONTWRITEBYTECODE 1
  --setenv QTWEBENGINE_CHROMIUM_FLAGS "--disable-gpu"
  --setenv QT_QUICK_BACKEND software
)

# Only the display socket is passed into the sandbox.
if [[ -n "${WAYLAND_DISPLAY:-}" && -S "/run/user/$UID_NUM/$WAYLAND_DISPLAY" ]]; then
  ARGS+=(--bind "/run/user/$UID_NUM/$WAYLAND_DISPLAY" "/run/user/$UID_NUM/$WAYLAND_DISPLAY")
  ARGS+=(--setenv WAYLAND_DISPLAY "$WAYLAND_DISPLAY")
fi
if [[ -n "${DISPLAY:-}" ]]; then
  ARGS+=(--setenv DISPLAY "$DISPLAY")
  if [[ -d /tmp/.X11-unix ]]; then
    ARGS+=(--ro-bind /tmp/.X11-unix /tmp/.X11-unix)
  fi
  AUTH_FILE="${XAUTHORITY:-$HOME/.Xauthority}"
  if [[ -f "$AUTH_FILE" ]]; then
    ARGS+=(--ro-bind "$AUTH_FILE" /tmp/.Xauthority --setenv XAUTHORITY /tmp/.Xauthority)
  fi
fi

LOG_TMP="$(mktemp -t docbrowser-launch.XXXXXX)"
if bwrap "${ARGS[@]}" /app/.venv/bin/python /app/main.py /documents >"$LOG_TMP" 2>&1; then
  rm -f -- "$LOG_TMP"
else
  EXIT_CODE=$?
  STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/docbrowser"
  mkdir -p -- "$STATE_DIR"
  mv -- "$LOG_TMP" "$STATE_DIR/last-launch.log"
  if grep -q 'loopback: Failed RTM_NEWADDR: Operation not permitted' "$STATE_DIR/last-launch.log"; then
    HINT="Ubuntu verweigert Bubblewrap die Einrichtung der Sandbox. Prüfe die AppArmor-Freigabe für /usr/bin/bwrap. Siehe README: Ubuntu/AppArmor."
  else
    HINT=""
  fi
  MESSAGE="$(printf 'Folio konnte nicht gestartet werden (Fehler %s).\n\n%s\n\nProtokoll: %s/last-launch.log\n\nLetzte Meldungen:\n%s' "$EXIT_CODE" "$HINT" "$STATE_DIR" "$(tail -n 8 "$STATE_DIR/last-launch.log")")"
  show_error "$MESSAGE"
  exit "$EXIT_CODE"
fi
