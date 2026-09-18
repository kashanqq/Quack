#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
generator="$repo_root/frontend/node_modules/.bin/openapi-typescript"
output="$repo_root/frontend/src/api/schema.d.ts"

if [[ ! -x "$generator" ]]; then
  echo "Missing frontend openapi-typescript dependency: $generator" >&2
  exit 1
fi

if [[ ! -d "$(dirname "$output")" ]]; then
  echo "Missing frontend API directory: $(dirname "$output")" >&2
  exit 1
fi

schema="$(mktemp)"
trap 'rm -f "$schema"' EXIT
(
  cd "$repo_root/backend"
  uv run --frozen python -c 'import json; from app.main import create_app; print(json.dumps(create_app().openapi()))' > "$schema"
)
"$generator" "$schema" -o "$output"
