#!/usr/bin/env bash
# Remove Folio's per-user installation; leave source files and documents intact.
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

if (($#)); then
  echo "Verwendung: ./uninstall.sh" >&2
  exit 2
fi

for name in folio docbrowser; do
  link="$HOME/.local/bin/$name"
  if [[ -L "$link" && "$(readlink -f -- "$link")" == "$APP_DIR/run.sh" ]]; then
    rm -- "$link"
    echo "Entfernt: $link"
  fi
done

"$APP_DIR/desktop_assets.sh" uninstall

venv="$APP_DIR/.venv"
if [[ -d "$venv" && -f "$venv/pyvenv.cfg" && ! -L "$venv" ]]; then
  rm -rf -- "$venv"
  echo "Entfernt: $venv"
fi

log="$HOME/.local/state/docbrowser/last-launch.log"
if [[ -f "$log" && ! -L "$log" ]]; then
  rm -- "$log"
  rmdir -- "$HOME/.local/state/docbrowser" 2>/dev/null || true
  echo "Entfernt: $log"
fi

echo "Folio wurde für diesen Benutzer deinstalliert. Projektordner und Dokumente bleiben erhalten."
