#!/bin/sh
# Fetch the SVG the fonts are drawn from, at the commits named in UPSTREAM.txt, and nothing
# else: the 3D renderings of fluentui-emoji weigh about a gigabyte and are never read.
#
#   fluentui-emoji  the art of every emoji, Flat and High Contrast
#   flag-icons      the flags of the countries and of England, Scotland and Wales
set -eu
cd "$(dirname "$0")"

fetch () {
  name=$1; url=$2; commit=$3; paths=$4
  dir=upstream/$name
  if [ ! -d "$dir/.git" ]; then
    git clone --quiet --filter=blob:none --no-checkout "$url" "$dir"
  fi
  git -C "$dir" sparse-checkout init --no-cone
  printf "$paths" > "$dir/.git/info/sparse-checkout"
  git -C "$dir" fetch --quiet origin "$commit"
  git -C "$dir" checkout --quiet "$commit"
  echo "$name at $(git -C "$dir" rev-parse HEAD)"
}

while read -r name url commit; do
  case $name in
    fluentui-emoji) fetch "$name" "$url" "$commit" '/assets/**/metadata.json\n/assets/**/Flat/*.svg\n/assets/**/High Contrast/*.svg\n/LICENSE\n' ;;
    flag-icons)     fetch "$name" "$url" "$commit" '/flags/4x3/*.svg\n/LICENSE\n' ;;
  esac
done < UPSTREAM.txt
