#!/bin/bash

echo "Formatting $PWD"

readonly ROOT_DIR=$(git rev-parse --show-toplevel)
readarray -t FILES <<<"$(find "$ROOT_DIR" -iname '*.py')"
readonly -a FILES

pyupgrade --py39-plus "${FILES[@]}"
isort "${FILES[@]}"
black "${FILES[@]}"
