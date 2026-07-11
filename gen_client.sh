#!/bin/bash

# npx @hey-api/openapi-ts -i http://localhost:5000/openapi.json -o src/generated_client -p @hey-api/client-fetch
openapi-generator-cli generate -i http://localhost:8000/openapi.json -g typescript-fetch -o src/api --additional-properties=typescriptThreePlus=true
