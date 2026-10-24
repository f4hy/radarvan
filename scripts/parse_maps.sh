#!/bin/bash
set -euo pipefail

mkdir -p jsons

while IFS= read -r line; do
    # Strip trailing * from paths
    map_path="${line%\*}"
    [ -z "$map_path" ] && continue

    # Use the map filename (without extension) as the output name
    map_name=$(basename "$map_path" .map)
    out="jsons/${map_name}.json"

    echo "Parsing: $map_path"
    ./mapparse --json "$map_path" > "$out"
done < maplist.txt
