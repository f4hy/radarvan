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

# NOTE: this regenerates radarvan/cncstats_model/body.py from scratch as plain
# BaseModel classes, clobbering the hand-converted `pydantic.dataclasses.dataclass
# (slots=True)` versions of ArgMetadata/BodyChunk (see the comment at the top of
# that file for why). Re-apply that conversion after running this script.

