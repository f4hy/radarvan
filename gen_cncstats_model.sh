#!/bin/bash
set -x
set -e

curl -o cncstats_schema.json https://cncstats.computersrfun.org/swagger/doc.json

datamodel-codegen  \
		--input cncstats_schema.json\
		--output radarvan/cncstats_model/ \
		--input-file-type jsonschema \
		--output-model-type pydantic_v2.BaseModel \
		--use-annotated \
		--use-standard-collections \
		--use-union-operator \
		--field-constraints \
		--snake-case-field \
		--collapse-root-models \
		--disable-timestamp

