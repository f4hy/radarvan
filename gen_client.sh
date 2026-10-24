#!/bin/bash
# Regenerates src/api from the app's OpenAPI spec (config: openapi-ts.config.mjs).
# The spec is built offline by scripts/dump_openapi.py, so no server is needed.
# Run through npx with TypeScript 6 because the generator imports TypeScript's JS API,
# which the project's TypeScript 7 does not ship.
set -euo pipefail
spec=$(mktemp --suffix=.json)
trap 'rm -f "$spec"' EXIT
uv run python scripts/dump_openapi.py "$spec"
rm -rf src/api
OPENAPI_INPUT="$spec" npx --yes -p typescript@6.0.3 -p @hey-api/openapi-ts@0.99.0 openapi-ts -f openapi-ts.config.mjs
