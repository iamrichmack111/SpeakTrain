#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/demo
rm -f docs/demo/speaktrain-playwright-demo.webm docs/demo/speaktrain-playwright-demo.gif docs/demo/speaktrain-playwright-demo.mp4
npx playwright test tests/e2e/demo.spec.js
ffmpeg -y -loglevel error \
  -i docs/demo/speaktrain-playwright-demo.webm \
  -vf "fps=6,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=96[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3" \
  -loop 0 docs/demo/speaktrain-playwright-demo.gif
ffmpeg -y -loglevel error -i docs/demo/speaktrain-playwright-demo.webm -movflags +faststart -pix_fmt yuv420p docs/demo/speaktrain-playwright-demo.mp4
printf 'Created %s\n' "docs/demo/speaktrain-playwright-demo.webm"
printf 'Created %s\n' "docs/demo/speaktrain-playwright-demo.gif"
printf 'Created %s\n' "docs/demo/speaktrain-playwright-demo.mp4"
