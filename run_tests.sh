#!/bin/sh
set -eu
PYTHONPATH=. python3 -m coverage run --branch --source=src -m unittest discover -s tests
PYTHONPATH=. python3 -m coverage report -m > coverage_report.txt
