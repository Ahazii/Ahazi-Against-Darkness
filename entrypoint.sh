#!/bin/sh
set -eu

APP_USER="${APP_USER:-appuser}"
APP_UID="${PUID:-${APP_UID:-10001}}"
APP_GID="${PGID:-${APP_GID:-10001}}"
DATA_DIR="${DATA_DIR:-/data}"
RULES_DIR="${DATA_DIR}/rules"
ASSETS_DIR="${DATA_DIR}/assets"
SUPPLEMENTS_DIR="${DATA_DIR}/Supplements"

if ! getent group "${APP_USER}" >/dev/null 2>&1; then
  groupadd --gid "${APP_GID}" "${APP_USER}"
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home "${APP_USER}"
fi

mkdir -p "${DATA_DIR}"
mkdir -p "${RULES_DIR}"
mkdir -p "${SUPPLEMENTS_DIR}"
mkdir -p "${ASSETS_DIR}/artwork/user"
mkdir -p "${ASSETS_DIR}/Application Artwork"
mkdir -p "${ASSETS_DIR}/icons/user"
mkdir -p "${ASSETS_DIR}/tiles/user"
mkdir -p "${ASSETS_DIR}/adventures"
mkdir -p "${ASSETS_DIR}/rules_art/local"

if [ -d "/app/data/rules" ]; then
  # Seed editable starter rules into persistent storage without overwriting user edits.
  cp -n /app/data/rules/*.json "${RULES_DIR}/" 2>/dev/null || true
fi

if [ -d "/app/assets/artwork/user" ]; then
  # Seed user-facing artwork placeholders beside game.db without overwriting local art.
  cp -Rn /app/assets/artwork/user/. "${ASSETS_DIR}/artwork/user/" 2>/dev/null || true
fi

if [ -d "/app/assets/Application Artwork" ]; then
  # Seed dashboard/application artwork placeholders beside game.db without overwriting local art.
  cp -Rn "/app/assets/Application Artwork/." "${ASSETS_DIR}/Application Artwork/" 2>/dev/null || true
fi

if [ -d "/app/assets/icons/user" ]; then
  # Seed starter user-facing map icons beside game.db without overwriting local art.
  cp -Rn /app/assets/icons/user/. "${ASSETS_DIR}/icons/user/" 2>/dev/null || true
fi

chown -R "${APP_UID}:${APP_GID}" "${DATA_DIR}"

exec gosu "${APP_UID}:${APP_GID}" "$@"
