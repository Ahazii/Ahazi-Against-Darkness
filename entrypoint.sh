#!/bin/sh
set -eu

APP_USER="${APP_USER:-appuser}"
APP_UID="${PUID:-${APP_UID:-10001}}"
APP_GID="${PGID:-${APP_GID:-10001}}"
DATA_DIR="${DATA_DIR:-/data}"

if ! getent group "${APP_USER}" >/dev/null 2>&1; then
  groupadd --gid "${APP_GID}" "${APP_USER}"
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home "${APP_USER}"
fi

mkdir -p "${DATA_DIR}"
chown -R "${APP_UID}:${APP_GID}" "${DATA_DIR}"

exec gosu "${APP_UID}:${APP_GID}" "$@"
