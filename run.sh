#!/bin/sh
set -eu
cd "$(dirname "$0")"
task_python="${PYTHON:-python3}"
if [ -z "${PYTHON:-}" ] && [ -x .venv/bin/python ]; then
    task_python=.venv/bin/python
fi
exec "$task_python" -m src.http_server "$@"
