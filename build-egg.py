"""Generate the importable egg from the versioned installer and variable definitions."""
import json
from pathlib import Path

HERE = Path(__file__).parent
variables = []


def var(name, env, default, rules, description):
    variables.append(dict(name=name, description=description, env_variable=env,
                          default_value=default, user_viewable=True, user_editable=True, rules=rules, field_type='text'))


var('GIANTS FS25 Product Key', 'FS25_PRODUCT_KEY', '', 'nullable|string|min:20|max:64|regex:/^[A-Za-z0-9-]+$/',
    'Separate GIANTS dedicated server license key. If empty, the server asks for it on start (BlueNet popup, or the console as a fallback) and stops after 60 seconds without input. Used for the download and the online activation. Pterodactyl stores startup variables in plain text; server owners and administrators can see them.')
var('Automatic GIANTS download', 'AUTO_DOWNLOAD', 'true', 'required|string|in:true,false',
    'Downloads the official installer with your key on first start. Alternatively upload the IMG/ZIP or Setup.exe with all BIN files to installer/.')
var('Installer download URL (optional)', 'FS25_DOWNLOAD_URL', '', 'nullable|url|max:2048',
    'Optional HTTPS link to the GIANTS installer instead of the portal lookup. Only use it if no installer was uploaded. Links can expire.')
var('Server name', 'SERVER_NAME', 'FS25 Server', 'required|string|max:60', 'Name shown in the FS25 server browser.')
var('Web port', 'WEB_PORT', '7999', 'required|integer|between:1025,65535',
    'Second allocation for the GIANTS web interface (TCP). It must be assigned to this server and differ from the primary game port. Plain HTTP; use a TLS reverse proxy for public access.')
var('Web user', 'WEB_USERNAME', 'admin', 'required|alpha_dash|max:32', 'Login for the GIANTS web interface.')
var('Web password', 'WEB_PASSWORD', '', 'required|string|min:12|max:64', 'Required: password for the GIANTS web interface.')
var('Game admin password', 'SERVER_ADMIN', '', 'required|string|min:8|max:16', 'Required: in-game administrator password. GIANTS allows at most 16 characters.')
var('Game password', 'SERVER_PASSWORD', '', 'nullable|string|max:16', 'Optional password to join, at most 16 characters.')
var('Player slots', 'SERVER_PLAYERS', '16', 'required|integer|between:1,16', 'Maximum number of players.')
var('Language', 'SERVER_REGION', 'de', 'required|string|size:2|alpha', 'Server language, e.g. de or en.')
var('Start map', 'SERVER_MAP', 'MapUS', 'required|string|max:191', 'Only for a new configuration: MapUS, MapAS or MapEU. Manage an existing world through the GIANTS portal.')
var('Savegame slot', 'SAVEGAME_INDEX', '1', 'required|integer|between:1,20', 'Savegame slot to start.')
var('Pause empty server', 'SERVER_PAUSE', '2', 'required|integer|in:0,1,2', 'GIANTS pause_game_if_empty (Standard: 2).')
var('Autosave interval', 'SERVER_SAVE_INTERVAL', '3', 'required|numeric|min:1|max:1440', 'Save interval in minutes (GIANTS uses minutes here, not seconds). Default: 3 minutes.')
var('Statistics interval', 'SERVER_STATS_INTERVAL', '360', 'required|numeric|min:60|max:31536000', 'Statistics interval in seconds.')
var('Crossplay', 'SERVER_CROSSPLAY', 'true', 'required|string|in:true,false', 'Allow crossplay.')
var('Activation timeout', 'ACTIVATION_TIMEOUT', '180', 'required|integer|between:60,900', 'Maximum time to wait for the GIANTS license activation, in seconds.')
var('Start timeout', 'START_TIMEOUT', '300', 'required|integer|between:60,1800', 'Maximum time to wait for gameplay; increase for large mod setups.')

script = '''#!/bin/ash
set -eu
mkdir -p /mnt/server/installer /mnt/server/game /mnt/server/config /mnt/server/logs
cat > /mnt/server/FS25-README.txt <<'EOF'
Farming Simulator 25 / Pterodactyl / no VNC

1. Startup: set WEB_PASSWORD and SERVER_ADMIN. Optionally set FS25_PRODUCT_KEY in advance.
   Without a key, the start asks for it (BlueNet popup, or the console for 60 seconds);
   without input the server stops.
2. Assign a second allocation for WEB_PORT (default 7999/TCP).
   The primary allocation is the game port (TCP and UDP).
3. Start: download, silent installation and activation happen on the first start.
   Alternatively upload the GIANTS IMG/ZIP or Setup.exe plus BIN files to installer/
   and set AUTO_DOWNLOAD=false.

game/   game installation
config/FarmingSimulator2025/   license files, mods, savegames, GIANTS configuration
.wine/  persistent Wine prefix (do not delete on reinstall)
logs/   technical installation and process logs

No VNC/noVNC port is required. The container only uses an invisible Xvfb display.
First activation depends on the GIANTS dialog layout and must be tested with your version.
The image contains no game files. A separate GIANTS server license is required.
EOF
echo 'FS25 directories prepared. Set the passwords under Startup. Set the key there or enter it in the console on start.'
'''
egg = dict(
    _comment='Custom FS25 egg. The image is pulled publicly from GHCR (https://github.com/SyntaxJason/fs25-pterodactyl).',
    meta=dict(version='PTDL_v2', update_url=None),
    exported_at='2026-10-23T00:00:00+02:00',
    name='Farming Simulator 25 (Wine, no VNC)',
    author='eggs@bluenet-hosting.com',
    description='FS25 on Wine with automatic GIANTS download, silent installation and dialog-based activation, without VNC. A separate GIANTS license is required. 8 GB RAM and 100 GB disk recommended. Primary allocation = game port, second allocation = WEB_PORT/TCP. First activation depends on the installer version.',
    features=['pid_limit'], docker_images={'FS25 Arch Wine': 'ghcr.io/syntaxjason/fs25-pterodactyl:latest'},
    file_denylist=[], startup='exec python /opt/fs25-ptero/runtime.py',
    config=dict(files='{}', startup=json.dumps(dict(done='FS25_READY:')), logs='{}', stop='^C'),
    scripts=dict(installation=dict(script=script, container='ghcr.io/pterodactyl/installers:alpine', entrypoint='ash')),
    variables=variables,
)
(HERE / 'egg-farming-simulator-25.json').write_text(json.dumps(egg, indent=4, ensure_ascii=False) + '\n')
print('Wrote egg-farming-simulator-25.json')
