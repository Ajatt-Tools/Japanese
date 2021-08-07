#!/usr/bin/env sh

readonly ROOT_DIR=$(git rev-parse --show-toplevel)
readonly BRANCH=$(git branch --show-current)
readonly ZIP_NAME=ajt_pitch_accent_$BRANCH.ankiaddon

cd -- "$ROOT_DIR" || exit 1

export ROOT_DIR BRANCH

git archive HEAD --format=zip --output "$ZIP_NAME"
# shellcheck disable=SC2016
git submodule foreach 'git archive HEAD --prefix=$path/ --format=zip --output "$ROOT_DIR/${path}_${BRANCH}.zip"'
zipmerge "$ZIP_NAME" ./*.zip
rm -- ./*.zip
