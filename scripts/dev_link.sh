#!/bin/bash

set -euo pipefail

root_dir=$(git rev-parse --show-toplevel)

if ! [[ $PWD -ef $root_dir ]]; then
	echo "not in root dir"
	exit 1
fi

links=(
	"kanjigrid/src:japanese/kanjigrid"
	"kanjigrid/data:japanese/kanjigrid/data"
)

for link in "${links[@]}"; do
	from=${link%%:*}
	to=${link#*:}
	if [[ -e $to ]]; then
		if [[ -L $to ]]; then
			unlink -- "$to"
		else
			echo "not a symlink: $to"
			exit 1
		fi
	fi
	ln -sr -- "$from" "$to"
done
echo "Done."
