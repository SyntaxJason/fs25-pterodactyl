#!/usr/bin/env bash
# Only for local development; the egg uses the published GHCR image.
# Run on the Wings host (or with the Docker context used by that Wings node).
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1; then
    echo 'Docker is missing. Run this script on the Wings host.' >&2
    exit 1
fi
platform=$(docker info --format '{{.OSType}}/{{.Architecture}}')
case "$platform" in
    linux/x86_64|linux/amd64) ;;
    *) echo "FS25/Wine needs a Linux x86_64 Docker host; detected: $platform" >&2; exit 1 ;;
esac

echo 'Building fs25-pterodactyl:local for this Wings host. The first download is several GB.'
docker build --tag fs25-pterodactyl:local .
docker run --rm --network none --entrypoint python fs25-pterodactyl:local -c '
import shutil, sys
sys.path.insert(0, "/opt/fs25-ptero")
import runtime
required = ("wine", "wineserver", "wineboot", "Xvfb", "xdotool", "7z", "python")
missing = [name for name in required if shutil.which(name) is None]
if missing:
    raise SystemExit("Missing runtime programs: " + ", ".join(missing))
print("Image and FS25 runtime verified.")
'
echo 'Done. Docker image for the egg: fs25-pterodactyl:local'
echo 'Restart the FS25 server in the panel now. Repeat on every Wings node you use.'
