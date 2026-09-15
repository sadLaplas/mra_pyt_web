#!/bin/sh
set -eu
PYTHONPATH=src exec python3 src/rpc_server.py
