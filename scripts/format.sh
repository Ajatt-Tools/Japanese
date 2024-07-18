#!/bin/bash

set -euo pipefail

readonly ROOT_DIR=$(git rev-parse --show-toplevel)

"$ROOT_DIR/japanese/ajt_common/format.sh"
prettier -w "$ROOT_DIR/japanese/note_type" "$ROOT_DIR/japanese/web"
