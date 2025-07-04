#!/bin/bash
#shellcheck disable=SC2086

exec uv run /app/main.py "$@"