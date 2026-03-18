#!/bin/bash
set -x
set -e

curl -o cncstats_schema.json http://cncstats.computersrfun.org:8080/swagger/doc.json

datamodel-codegen  --input cncstats_schema.json --input-file-type jsonschema --output radarvan/cncstats_model/
