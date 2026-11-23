#!/usr/bin/env bash
# Installs the "Historia Animada" template (Linux) for animado/hacer.py. Safe to run again: it only adds what is missing.
#   bash animado/instalar.sh [folder]      (default: $HISTORIA_ANIMADA or ~/historia-animada)
# The template is downloaded from its author's site every time a fresh workspace needs it: its license allows making
# and monetizing videos but not redistributing it, so it must never be committed to this (public) repo.
set -euo pipefail
DEST="${1:-${HISTORIA_ANIMADA:-$HOME/historia-animada}}"
BASE="https://yss.ale-ferr.com/gratis/historia-animada/descarga/v3"
SHA="f32170b3fbc8415833dce9170ce2f433d285df8ba1c227fc68a2082e8a569314"
NODE_V="v24.22.0"
mkdir -p "$DEST" && cd "$DEST"

if [ ! -f src/historia/VideoTerra.tsx ]; then
  echo "Downloading the template (about 90 MB)..."
  rm -f .h.zip
  for i in 1 2 3 4 5; do curl -fsSL "$BASE/parte$i.bin" >> .h.zip; done
  if [ "$(sha256sum .h.zip | cut -d' ' -f1)" != "$SHA" ]; then
    rm -f .h.zip
    echo "STOP: the template download does not match the checked version (the author changed it). Do not use it; tell Juan." >&2
    exit 2
  fi
  unzip -oq .h.zip && rm -f .h.zip
fi

if [ ! -x node/bin/node ]; then
  echo "Downloading Node $NODE_V..."
  curl -fsSL "https://nodejs.org/dist/$NODE_V/node-$NODE_V-linux-x64.tar.xz" -o node.tar.xz
  mkdir -p node && tar -xJf node.tar.xz -C node --strip-components=1 && rm node.tar.xz
fi
export PATH="$DEST/node/bin:$PATH"

if [ ! -d node_modules/remotion ]; then
  echo "Installing the video engine..."
  npm ci --no-audit --no-fund --loglevel=error
fi
npx remotion browser ensure >/dev/null

python3 -c "import shapely" 2>/dev/null || pip install --break-system-packages -q shapely
mkdir -p public/mapas public/videos
echo "Historia Animada ready in $DEST"
