#!/bin/bash

set -euo pipefail

readonly NC='\033[0m'
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'

rm -v -- ./*.ankiaddon 2>/dev/null || true

for exe in git zip zipmerge; do
	if ! command -v "$exe" >/dev/null; then
		echo -e "${RED}Missing dependency:${NC} $exe"
		exit 1
	fi
done

readonly ADDON_NAME=ajt_japanese
readonly ROOT_DIR=$(git rev-parse --show-toplevel)
readonly BRANCH=${1:-$(git branch --show-current)}
readonly ZIP_NAME=${ADDON_NAME}_${BRANCH}.ankiaddon

cd -- "$ROOT_DIR" || exit 1
export ROOT_DIR BRANCH
git archive "$BRANCH" --format=zip --output "$ZIP_NAME"
# shellcheck disable=SC2016
git submodule foreach 'git archive HEAD --prefix=$path/ --format=zip --output "$ROOT_DIR/${path}_${BRANCH}.zip"'
zipmerge "$ZIP_NAME" ./*.zip
rm -- ./*.zip
echo -e "${GREEN}Done.${NC}"
