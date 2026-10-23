#!/usr/bin/env bash
# Run on the Wings host (or with the Docker context used by that Wings node).
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1; then
    echo 'Docker fehlt. Dieses Skript auf dem Wings-Host ausfuehren.' >&2
    exit 1
fi
platform=$(docker info --format '{{.OSType}}/{{.Architecture}}')
case "$platform" in
    linux/x86_64|linux/amd64) ;;
    *) echo "FS25/Wine benoetigt einen Linux-x86_64-Docker-Host; erkannt: $platform" >&2; exit 1 ;;
esac

echo 'Baue fs25-pterodactyl:local für diesen Wings-Host. Der erste Download umfasst mehrere GB.'
docker build --tag fs25-pterodactyl:local .
docker run --rm --network none --entrypoint python fs25-pterodactyl:local -c '
import shutil, sys
sys.path.insert(0, "/opt/fs25-ptero")
import runtime
required = ("wine", "wineserver", "wineboot", "Xvfb", "xdotool", "7z", "python")
missing = [name for name in required if shutil.which(name) is None]
if missing:
    raise SystemExit("Fehlende Laufzeitprogramme: " + ", ".join(missing))
print("Image und FS25-Laufzeit erfolgreich geprueft.")
'
echo 'Fertig. Docker-Image im Egg: fs25-pterodactyl:local'
echo 'Den FS25-Server jetzt im Panel erneut starten. Auf jedem verwendeten Wings-Node wiederholen.'
