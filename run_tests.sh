#!/bin/sh
set -eu
cd "$(dirname "$0")"
task_python="${PYTHON:-python3}"
"$task_python" -m pycodestyle src tests
"$task_python" -m coverage run -m unittest discover -b -s tests
"$task_python" -m coverage report -m > coverage_report.txt
"$task_python" -m coverage report -m
