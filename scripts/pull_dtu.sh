#!/usr/bin/env bash
# Alternative for DTU-internal cron if inbound SSH from GitHub Actions is blocked.
# Run as the web service account. Checkout must be dedicated and clean.
set -euo pipefail
: "${HATA_REPO:?Set HATA_REPO to local git checkout of jakoblem/hata}"
: "${HATA_WEB_ROOT:?Set HATA_WEB_ROOT to the dedicated HATA docroot}"
[[ "$HATA_WEB_ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo 'Unsafe target'; exit 2; }
[[ "$HATA_WEB_ROOT" != / && "$HATA_WEB_ROOT" != /home && "$HATA_WEB_ROOT" != /var/www ]] || exit 2
[[ -d "$HATA_WEB_ROOT" && -w "$HATA_WEB_ROOT" ]] || { echo 'Missing or read-only web root'; exit 2; }
[[ -f "$HATA_REPO/site/index.html" ]] || { echo 'Not a HATA checkout'; exit 2; }
git -C "$HATA_REPO" fetch --quiet --depth=1 origin main
git -C "$HATA_REPO" reset --hard --quiet FETCH_HEAD
# WARNING: Delete files not in site/; ONLY use with a dedicated target dir.
rsync -az --delete-delay --delay-updates "$HATA_REPO/site/" "$HATA_WEB_ROOT/"
