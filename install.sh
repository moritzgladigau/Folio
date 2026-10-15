#!/usr/bin/env bash
# Ubuntu installer. Uses sudo only for missing system packages or the bwrap profile.
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
INSTALL_DESKTOP=false
OPEN_ROOT=""

usage() {
  echo "Verwendung: ./install.sh [--desktop] [Dokumentenordner]" >&2
}

while (($#)); do
  case "$1" in
    --desktop) INSTALL_DESKTOP=true ;;
    --help|-h) usage; exit 0 ;;
    -*) usage; exit 2 ;;
    *)
      if [[ -n "$OPEN_ROOT" ]]; then usage; exit 2; fi
      OPEN_ROOT="$1"
      ;;
  esac
  shift
done

if [[ -n "$OPEN_ROOT" ]]; then
  if [[ ! -d "$OPEN_ROOT" ]]; then
    echo "Dokumentenordner existiert nicht: $OPEN_ROOT" >&2
    exit 2
  fi
  OPEN_ROOT="$(realpath -e -- "$OPEN_ROOT")"
fi

if [[ ! -f /etc/os-release ]] || ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "Dieses Installationsskript ist für Ubuntu vorgesehen." >&2
  exit 1
fi
if ! command -v dpkg-query >/dev/null 2>&1 || ! command -v apt-get >/dev/null 2>&1; then
  echo "Ubuntu-Paketverwaltung fehlt." >&2
  exit 1
fi

as_root() {
  if (( EUID == 0 )); then
    "$@"
  else
    if ! command -v sudo >/dev/null 2>&1; then
      echo "sudo wird für fehlende Systempakete oder das AppArmor-Profil benötigt." >&2
      return 1
    fi
    sudo "$@"
  fi
}

missing_packages() {
  local package
  for package in "$@"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
      printf '%s\n' "$package"
    fi
  done
}

mapfile -t MISSING < <(missing_packages \
  python3 python3-venv bubblewrap apparmor libegl1 libopengl0 \
  libxcb-cursor0 libxkbcommon-x11-0)
if ((${#MISSING[@]})); then
  echo "Installiere fehlende Ubuntu-Pakete: ${MISSING[*]}"
  as_root apt-get install "${MISSING[@]}"
fi

sandbox_probe() {
  bwrap --unshare-all --ro-bind / / /usr/bin/true
}

if ! PROBE_OUTPUT="$(sandbox_probe 2>&1)"; then
  if [[ "$PROBE_OUTPUT" != *"loopback: Failed RTM_NEWADDR: Operation not permitted"* ]]; then
    echo "Bubblewrap kann keine Sandbox starten: $PROBE_OUTPUT" >&2
    exit 1
  fi

  echo "Ubuntu blockiert die Bubblewrap-Sandbox; richte das gezielte AppArmor-Profil ein."
  PROFILE_SOURCE=/usr/share/apparmor/extra-profiles/bwrap-userns-restrict
  PROFILE_TARGET=/etc/apparmor.d/bwrap-userns-restrict
  if [[ ! -e "$PROFILE_TARGET" && ! -f "$PROFILE_SOURCE" ]]; then
    as_root apt-get install apparmor-profiles
  fi
  if [[ ! -e "$PROFILE_TARGET" && ! -f "$PROFILE_SOURCE" ]]; then
    echo "Das Ubuntu-Profil fehlt: $PROFILE_SOURCE" >&2
    exit 1
  fi
  if [[ ! -e "$PROFILE_TARGET" ]]; then
    as_root install -m 0644 "$PROFILE_SOURCE" "$PROFILE_TARGET"
  fi
  as_root apparmor_parser -r "$PROFILE_TARGET"
  if ! PROBE_OUTPUT="$(sandbox_probe 2>&1)"; then
    echo "Bubblewrap bleibt blockiert: $PROBE_OUTPUT" >&2
    exit 1
  fi
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"
cd "$APP_DIR"
"$APP_DIR/.venv/bin/python" -m unittest discover -s "$APP_DIR/tests" -p 'test_*.py'

chmod +x "$APP_DIR/run.sh"
mkdir -p "$HOME/.local/bin"
ln -sfn "$APP_DIR/run.sh" "$HOME/.local/bin/folio"
if [[ -L "$HOME/.local/bin/docbrowser" && "$(readlink -f "$HOME/.local/bin/docbrowser")" == "$APP_DIR/run.sh" ]]; then
  rm "$HOME/.local/bin/docbrowser"
fi

if "$INSTALL_DESKTOP"; then
  "$APP_DIR/desktop_assets.sh" install
fi

echo "Installation abgeschlossen. Start: $APP_DIR/run.sh [Dokumentenordner]"
if [[ -n "$OPEN_ROOT" ]]; then
  "$APP_DIR/run.sh" "$OPEN_ROOT"
fi
