#!/usr/bin/env bash
# Install/remove Folio's per-user desktop entry and icon theme assets.
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DESKTOP="$HOME/.local/share/applications/docbrowser.desktop"
ICON_NAME=folio-readonly
ICON_ROOT="$HOME/.local/share/icons/hicolor"

icon_source() {
  local size="$1"
  if [[ "$size" == scalable ]]; then
    printf '%s/assets/%s.svg' "$APP_DIR" "$ICON_NAME"
  else
    printf '%s/assets/%s-%s.png' "$APP_DIR" "$ICON_NAME" "$size"
  fi
}

icon_target() {
  local size="$1"
  if [[ "$size" == scalable ]]; then
    printf '%s/scalable/apps/%s.svg' "$ICON_ROOT" "$ICON_NAME"
  else
    printf '%s/%sx%s/apps/%s.png' "$ICON_ROOT" "$size" "$size" "$ICON_NAME"
  fi
}

case "${1:-}" in
  install)
    for size in 32 64 128 256 scalable; do
      source="$(icon_source "$size")"
      target="$(icon_target "$size")"
      mkdir -p -- "$(dirname -- "$target")"
      install -m 0644 "$source" "$target"
    done
    mkdir -p -- "$(dirname -- "$DESKTOP")"
    sed "s|^Exec=.*|Exec=\"$APP_DIR/run.sh\" %f|" "$APP_DIR/docbrowser.desktop" > "$DESKTOP"
    echo "Folio-Starter und Icon installiert."
    ;;
  uninstall)
    owns_desktop=false
    if [[ -f "$DESKTOP" ]] && grep -Fxq "Exec=\"$APP_DIR/run.sh\" %f" "$DESKTOP"; then
      owns_desktop=true
      rm -- "$DESKTOP"
      echo "Entfernt: $DESKTOP"
    fi
    for size in 32 64 128 256 scalable; do
      source="$(icon_source "$size")"
      target="$(icon_target "$size")"
      if [[ -f "$target" && ! -L "$target" ]]; then
        if "$owns_desktop" || { [[ ! -e "$DESKTOP" ]] && cmp -s -- "$source" "$target"; }; then
          rm -- "$target"
          echo "Entfernt: $target"
        fi
      fi
    done
    ;;
  *)
    echo "Verwendung: ./desktop_assets.sh install|uninstall" >&2
    exit 2
    ;;
esac
