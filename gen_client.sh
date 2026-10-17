#!/bin/bash
# Regenerates src/api from the running server's spec (config: openapi-ts.config.mjs).
# Run through npx with TypeScript 6 because the generator imports TypeScript's JS API,
# which the project's TypeScript 7 does not ship.
set -euo pipefail
rm -rf src/api
npx --yes -p typescript@6.0.3 -p @hey-api/openapi-ts@0.99.0 openapi-ts -f openapi-ts.config.mjs
