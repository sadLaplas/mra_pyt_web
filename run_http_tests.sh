#!/bin/sh
set -eu
cd "$(dirname "$0")"
task_python="${PYTHON:-python3}"
"$task_python" -m pycodestyle src tests
"$task_python" -m coverage run --branch --source=src.http_server,src.http_store,src.http_client,src.ean8,src.task_runner -m unittest discover -b -s tests -p 'test_http*.py'
"$task_python" -m coverage run --append --branch --source=src.ean8 -m unittest discover -b -s tests -p 'test_ean8.py'
"$task_python" -m coverage report -m > http_coverage_report.txt
"$task_python" -m coverage report -m
