"""Generate the importable egg from the versioned installer and variable definitions."""
import json
from pathlib import Path

HERE = Path(__file__).parent
variables = []


def var(name, env, default, rules, description):
    variables.append(dict(name=name, description=description, env_variable=env,
                          default_value=default, user_viewable=True, user_editable=True, rules=rules, field_type='text'))


var('GIANTS FS25 Product Key', 'FS25_PRODUCT_KEY', '', 'nullable|string|min:20|max:64|regex:/^[A-Za-z0-9-]+$/',
    'Separate GIANTS-Version für den Dedicated Server. Leer: BlueNet fragt beim Start per Popup nach dem Key (alternativ Konsole). Nach 60 Sekunden ohne Eingabe wird gestoppt. Wird für Download und Online-Aktivierung verwendet. Nicht in den Startbefehl schreiben. Pterodactyl speichert Startup-Variablen im Klartext; für Serverbesitzer und Administratoren sichtbar.')
var('Automatischer GIANTS-Download', 'AUTO_DOWNLOAD', 'true', 'required|string|in:true,false',
    'Laedt beim ersten Start den offiziellen Installer mit deinem Key. Alternativ IMG/ZIP oder Setup.exe mit allen BIN-Dateien nach installer/ hochladen.')
var('Installer Download URL (optional)', 'FS25_DOWNLOAD_URL', '', 'nullable|url|max:2048',
    'Optionaler HTTPS-Link zum GIANTS-Installer statt Portal-Erkennung. Nur verwenden, wenn kein Installer hochgeladen wurde. Links koennen ablaufen.')
var('Servername', 'SERVER_NAME', 'FS25 Server', 'required|string|max:60', 'Name im FS25 Serverbrowser.')
var('Web-Port', 'WEB_PORT', '7999', 'required|integer|between:1025,65535',
    'Zweite Allocation für das GIANTS-Webinterface (TCP). Muss diesem Server zugewiesen sein und sich vom primaeren Spielport unterscheiden. HTTP; für oeffentlichen Betrieb TLS-Reverse-Proxy verwenden.')
var('Web-Benutzer', 'WEB_USERNAME', 'admin', 'required|alpha_dash|max:32', 'Login für das GIANTS-Webinterface.')
var('Web-Passwort', 'WEB_PASSWORD', '', 'required|string|min:12|max:64', 'Pflichtfeld: Passwort für das GIANTS-Webinterface.')
var('Spiel-Adminpasswort', 'SERVER_ADMIN', '', 'required|string|min:8|max:16', 'Pflichtfeld: Administratorpasswort im Spiel. GIANTS erlaubt maximal 16 Zeichen.')
var('Spiel-Passwort', 'SERVER_PASSWORD', '', 'nullable|string|max:16', 'Optionales Passwort zum Beitreten, maximal 16 Zeichen.')
var('Spielerzahl', 'SERVER_PLAYERS', '16', 'required|integer|between:1,16', 'Maximale Spielerzahl.')
var('Sprache', 'SERVER_REGION', 'de', 'required|string|size:2|alpha', 'Sprache des Servers, z.B. de oder en.')
var('Startkarte', 'SERVER_MAP', 'MapUS', 'required|string|max:191', 'Nur für neue Konfiguration: MapUS, MapAS oder MapEU. Existierende Welt ueber GIANTS verwalten.')
var('Savegame-Slot', 'SAVEGAME_INDEX', '1', 'required|integer|between:1,20', 'Zu startender Savegame-Slot.')
var('Leeren Server pausieren', 'SERVER_PAUSE', '2', 'required|integer|in:0,1,2', 'GIANTS pause_game_if_empty (Standard: 2).')
var('Autosave-Intervall', 'SERVER_SAVE_INTERVAL', '3', 'required|numeric|min:1|max:1440', 'Speicherintervall in Minuten. GIANTS verwendet hier Minuten, nicht Sekunden. Standard: 3 Minuten.')
var('Statistik-Intervall', 'SERVER_STATS_INTERVAL', '360', 'required|numeric|min:60|max:31536000', 'Statistikintervall in Sekunden.')
var('Crossplay', 'SERVER_CROSSPLAY', 'true', 'required|string|in:true,false', 'Crossplay zulassen.')
var('Aktivierungs-Timeout', 'ACTIVATION_TIMEOUT', '180', 'required|integer|between:60,900', 'Maximale Wartezeit auf die GIANTS-Lizenzaktivierung in Sekunden.')
var('Start-Timeout', 'START_TIMEOUT', '300', 'required|integer|between:60,1800', 'Maximale Wartezeit auf Gameplay; bei grossen Mod-Welten erhoehen.')

script = '''#!/bin/ash
set -eu
mkdir -p /mnt/server/installer /mnt/server/game /mnt/server/config /mnt/server/logs
cat > /mnt/server/FS25-README.txt <<'EOF'
Farming Simulator 25 / Pterodactyl / ohne VNC

1. Startup: WEB_PASSWORD und SERVER_ADMIN setzen. FS25_PRODUCT_KEY optional vorab setzen.
   Ohne Key folgt beim Start ein BlueNet-Popup (alternativ Konsole, 60 Sekunden); ohne Eingabe stoppt der Server.
2. Zweite Allocation für WEB_PORT (Standard 7999/TCP) zuweisen.
   Die primaere Allocation ist der Spielport (TCP und UDP).
3. Starten: Download, Silent-Installation und Aktivierung erfolgen beim ersten Start.
   Alternativ GIANTS IMG/ZIP oder Setup.exe plus BIN-Dateien nach installer/ hochladen.
   Für den manuellen Weg AUTO_DOWNLOAD=false setzen.

game/   Spielinstallation
config/FarmingSimulator2025/   Lizenzdateien, Mods, Savegames, GIANTS-Konfiguration
.wine/  persistentes Wine-Profil (bei Neuinstallation nicht loeschen)
logs/   technische Installations- und Prozesslogs

Kein VNC/noVNC-Port erforderlich. Der Container nutzt nur ein unsichtbares Xvfb-Display.
Die Erstaktivierung haengt vom GIANTS-Dialoglayout ab und muss mit deiner Version getestet werden.
Das Image enthaelt keine Spieldateien. Separate GIANTS-Serverlizenz erforderlich.
EOF
echo 'FS25-Verzeichnisse vorbereitet. Passwoerter unter Startup setzen. Key dort setzen oder beim Start in der Konsole eingeben.'
'''
egg = dict(
    _comment='Custom FS25 egg. Image wird oeffentlich von GHCR gezogen (https://github.com/SyntaxJason/fs25-pterodactyl).',
    meta=dict(version='PTDL_v2', update_url=None),
    exported_at='2026-10-23T00:00:00+02:00',
    name='Farming Simulator 25 (Wine, ohne VNC)',
    author='local@example.com',
    description='FS25 auf Wine mit automatischem GIANTS-Download, Silent-Installation und Dialog-Aktivierung ohne VNC. Separate GIANTS-Lizenz erforderlich. 8 GB RAM und 100 GB Disk empfohlen. Primaere Allocation = Spielport, zweite Allocation = WEB_PORT/TCP. Erstaktivierung versionsabhaengig.',
    features=['pid_limit'], docker_images={'FS25 Arch Wine': 'ghcr.io/syntaxjason/fs25-pterodactyl:latest'},
    file_denylist=[], startup='exec python /opt/fs25-ptero/runtime.py',
    config=dict(files='{}', startup=json.dumps(dict(done='FS25_READY:')), logs='{}', stop='^C'),
    scripts=dict(installation=dict(script=script, container='ghcr.io/pterodactyl/installers:alpine', entrypoint='ash')),
    variables=variables,
)
(HERE / 'egg-farming-simulator-25.json').write_text(json.dumps(egg, indent=4, ensure_ascii=False) + '\n')
print('Wrote egg-farming-simulator-25.json')
