#!/bin/bash
set -eu
cd "$(dirname "$0")"
if ! grep -q '<Entry' subplans/waivers.xml; then
  echo 'ERROR: no waiver entries exist, add before enabling job'
  exit 1
fi

shopt -s nullglob
set -x
for f in _control.*waivers*; do
  git mv "$f" "${f#_}"
done
git add subplans/waivers.xml
