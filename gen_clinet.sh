#!/bin/bash

npx @hey-api/openapi-ts -i http://localhost:5000/openapi.json -o src/generated_client -p @hey-api/client-fetch
