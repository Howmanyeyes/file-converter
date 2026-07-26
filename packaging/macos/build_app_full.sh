#!/bin/zsh

set -euo pipefail

SCRIPT_DIRECTORY="$(cd "$(dirname "$0")" && pwd)"
exec "${SCRIPT_DIRECTORY}/_build_app.sh" full
