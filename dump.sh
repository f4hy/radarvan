#!/bin/bash

curl -X 'GET' \
  'https://www.radarvan.com/api/files/' \
  -H 'accept: application/json' \
	-o file_dump.json

curl -X 'GET' \
  'http://localhost:8000/api/replays/' \
  -H 'accept: application/json' \
	-o replay_json_dump.json
