#!/bin/bash

set -euo pipefail

readonly ROOT_DIR=$(git rev-parse --show-toplevel)

"$ROOT_DIR/japanese/ajt_common/package.sh" \
	--package "AJT Japanese" \
	--name "AJT Japanese" \
	--root "japanese" \
	"$@"
