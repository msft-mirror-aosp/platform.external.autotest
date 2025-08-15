#!/bin/bash
set -eu
cd "$(dirname "$0")"
if grep -q '<Entry' subplans/waivers.xml; then
  echo 'ERROR: waiver entries exist, remove before disabling job'
  exit 1
fi

shopt -s nullglob
set -x
for f in control.*waivers*; do
  git mv "$f" "_$f"
done
git add subplans/waivers.xml
