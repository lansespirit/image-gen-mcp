#!/bin/bash
cd "$(dirname "$0")"

# Load environment variables from .env if it exists
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi

exec uv run python -m gpt_image_mcp.server