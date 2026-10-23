# FS25 für Pterodactyl, ohne VNC

Ein eigenes PTDL_v2-Egg und ein Pterodactyl-Adapter für
[wine-gameservers/arch-fs25server](https://github.com/wine-gameservers/arch-fs25server).
Es startet weder VNC/noVNC noch einen Desktop oder Browser. Wine verwendet
Xvfb mit einem unsichtbaren Display. Die Online-Aktivierung erfolgt beim
ersten Start ueber den GIANTS-Dialog mit xdotool.
Das Adapter-Image aktualisiert das im Basisimage vorhandene Wine Staging 10.1
auf Wine 11.0 und ergaenzt passende Lavapipe-/LLVM-Bibliotheken.

## Lokal eingerichtet

- Projekt: `/run/media/syntaxjason/Code/Biz/Pterodactyl/fs25-egg`
- Image: `fs25-pterodactyl:local`
- Egg-ID: `16`
- Server: **FS25 Headless Test**, ID `23`, Kennung `3b0360d9`
- [Konsole](http://localhost:8091/server/3b0360d9)
- [Startup](http://localhost:8091/server/3b0360d9/startup)
- Spielport: `10825` TCP/UDP; Webport: `7999` TCP
- RAM: 8192 MiB, Disk: 102400 MiB, CPU: 400 %, Swap: 0

Beide Allocations sind als `127.0.0.1` angelegt. Dein Wings bildet Loopback
beim Docker-Binding auf seine Bridge `172.31.250.1` ab. Das GIANTS-Webinterface
ist nach erfolgreichem Start daher lokal unter
[http://172.31.250.1:7999](http://172.31.250.1:7999) erreichbar.
Die Spiel-Allocation für einen extern erreichbaren Server entsprechend aendern.

## Jetzt eintragen

1. Auf der Startup-Seite `FS25_PRODUCT_KEY` setzen oder leer lassen.
   Mit der lokalen BlueNet-Erweiterung ab Version 1.0.44 erscheint ohne Key beim
   Start auf den Serverseiten ein **Popup** für deinen separaten GIANTS-Server-Key.
   Der Key wird dort maskiert eingegeben und als Startup-Variable gespeichert;
   der wartende Prozess startet anschliessend neu. Abbrechen, Schliessen oder
   ein leeres Feld stoppen den Server. Ohne Eingabe bleibt der 60-Sekunden-Timeout
   des Containers aktiv. Der Key wird dabei nicht als Konsolenbefehl gesendet.
   Ohne BlueNet bleibt die Konsolenabfrage als Alternative erhalten. Du hast 60 Sekunden Zeit. Keine Antwort, leere Eingabe,
   `abbrechen` oder geschlossenes stdin stoppen den Server sauber (Exitcode 0),
   bevor Wine oder ein Download startet. Die Panel-Konsole sendet keine leeren
   Befehle; dort `abbrechen` verwenden oder den Timeout abwarten.
   Eine Konsoleneingabe gilt nur für diesen Start; dauerhaft den Key in Startup
   setzen. Das Terminal-Echo ist waehrend der Abfrage deaktiviert; die Panel-
   Befehlshistorie speichert gesendete Befehle trotzdem im Browser. Für den
   dauerhaften Key daher das Startup-Feld verwenden.
   Auf dem lokalen Testserver ist dein echter Key bereits hinterlegt.
2. `AUTO_DOWNLOAD=true` ist lokal aktiviert. Alternativ den GIANTS-Installer nach `installer/`
   hochladen und `AUTO_DOWNLOAD=false` beibehalten. IMG/ZIP oder `Setup.exe` mit
   allen zugehoerigen BIN-Dateien werden unterstuetzt.
3. `WEB_PASSWORD` und `SERVER_ADMIN` sind für den lokalen Test zufaellig erzeugt
   worden; unter Startup nachsehen oder eigene setzen. Das Spiel-Adminpasswort
   darf bei GIANTS maximal 16 Zeichen haben.
4. Starten. Download, Extraktion, Silent-Installation und Erstaktivierung brauchen
   beim ersten Start entsprechend Zeit. Spaetere Starts verwenden die vorhandenen Dateien.

Der automatische Download meldet deinen Key beim offiziellen GIANTS-Portal an
und sendet das Windows-IMG-Downloadformular ab. Auch die frueheren direkten
CDN-Links werden unterstuetzt. Ein abgelaufener Link oder eine geaenderte
Portalseite laesst sich durch einen manuellen Upload umgehen. Es werden keine
Spieldateien mitgeliefert. Die Steam-Installation des lokalen PCs wird nicht verwendet.

Pterodactyl speichert Startup-Variablen im Klartext in seiner Datenbank und gibt
sie als Container-Umgebung weiter. Serverbesitzer und Administratoren koennen
sie sehen. Der Adapter schreibt den Key nicht in den Startbefehl oder eigene
Konsolenmeldungen und reicht ihn an xdotool ueber stdin statt argv weiter.

## Ablauf und Persistenz

- `.wine/`: Wine-Profil und Registry; wird nicht bei jedem Start geloescht.
- `game/Farming Simulator 2025/`: installierte Spieldateien.
- `config/FarmingSimulator2025/`: Lizenzdateien, Mods, Savegames und GIANTS-Konfiguration.
- `installer/`: hochgeladene/heruntergeladene Installationsmedien, bleiben erhalten.
- `logs/`: Installations-, Display-, Aktivierungs- und Prozesslogs.

Die beiden XML-Konfigurationen werden mit einem XML-Parser aktualisiert.
Unbekannte Einstellungen, Mod-Auswahl und die Karte einer vorhandenen Welt
bleiben erhalten. Startup-Variablen für Name, Port, Passwoerter und Slot gelten
bei jedem Start. Kartenwechsel einer bestehenden Konfiguration im GIANTS-Portal
vornehmen; für einen anderen vorhandenen Slot `SAVEGAME_INDEX` setzen.
Die Web-Zugangsdaten stehen im GIANTS-Block `initial_admin` und initialisieren
den ersten Web-Benutzer. Einen bereits angelegten Web-Benutzer spaeter im
GIANTS-Portal aendern und die Egg-Variablen entsprechend nachziehen.

Das Spiel wird durch `dedicatedServer.exe` und einen authentifizierten HTTP-POST
auf das GIANTS-Webinterface gestartet. Erst eine neue Gameplay-Meldung in den
Spiel-Logs erzeugt `FS25_READY:` und damit den Pterodactyl-Status „Running“.
Die Serverlogs inklusive der datierten `log_*.txt`-Engine-Logs werden
fortlaufend in die Konsole uebertragen. Eine fruehe Meldung „Started network game“
zaehlt noch nicht als abgeschlossener Kartenstart.

Ein normaler Stop (`SIGINT`/`SIGTERM`) fordert beim GIANTS-Portal das Stoppen
der Spielsession an und wartet bis zu 45 Sekunden, bevor Wine beendet wird.
Dem Container mindestens 60 Sekunden Stop-Frist geben.
Damit der Abbruch ohne License Key dauerhaft gestoppt bleibt, muss Wings saubere
Exits respektieren. Auf dem lokalen Node ist in `config.yml`
`system.crash_detection.detect_clean_exit_as_crash: false` gesetzt. Die normale
Crash-Erkennung (`enabled: true`) bleibt aktiv. Diese Option gilt für den ganzen
Node und muss auf weiteren Nodes ebenfalls passend gesetzt werden; siehe
[Wings-Konfiguration](https://docs.pterodactyl.io/v2/wings/configuration#crash-detection).
Dieser Stop fordert keinen zusaetzlichen manuellen Weltspeichervorgang an.
Für Spielfortschritt gelten die GIANTS-Autosaves und manuelles Speichern im Spiel.
`SERVER_SAVE_INTERVAL` wird in **Minuten** gemessen; der Standard ist **3 Minuten**.

## Auf einem anderen Wings-Host

Das Egg verwendet das oeffentliche Image `ghcr.io/syntaxjason/fs25-pterodactyl:latest`
(Linux/amd64, ca. 7,3 GB entpackt). Wings zieht es beim ersten Start selbst;
weder Bauen noch `install-wings.sh` sind noetig. Das Image enthaelt weder
Spieldateien noch Lizenzen. Gebaut wird es per GitHub Actions
(`.github/workflows/image.yml`); der Workflow prueft nach jedem Push, dass das
Image ohne Anmeldung gezogen werden kann.

`install-wings.sh` und `docker build -t fs25-pterodactyl:local .` bleiben nur
für lokale Entwicklung. Egg neu erzeugen: `python3 build-egg.py`, dann
`egg-farming-simulator-25.json` unter Admin → Eggs importieren.
Pro Server eine primaere Spiel-Allocation und eine zweite Web-Allocation
zuweisen; `WEB_PORT` muss auf die zweite Allocation passen.

Pterodactyl 2 akzeptiert das PTDL_v2-Format; siehe
[Egg-Dokumentation](https://docs.pterodactyl.io/v2/guides/egg-creation/creating-custom-egg).
Die primaere Spielport-Variable `SERVER_PORT` kommt von Wings und ist nicht
als manuell editierbares Egg-Feld angelegt.

## Grenzen und Teststand

Mit **FS25 1.25.0.0** lokal verifiziert: echter GIANTS-Download,
Extraktion, Silent-Installation, automatische Online-Aktivierung, Spielstart bis
„Entered Gameplay“, Stop ueber GIANTS und Neustart mit vorhandener Aktivierung.
Die Aktivierungsautomatik orientiert sich am ESD-Launcher mit 1280×720-Display
und unterstuetzt dessen Titel mit Buildnummer. Andere GIANTS-Dialoglayouts koennen
Anpassungen brauchen. Ein Timeout wird als Fehler gemeldet.
Eine Client-Verbindung und Speichern/Wiederherstellen echten Spielfortschritts
sind noch nicht getestet.

Automatische DLC-Installation und automatische Spielupdates sind nicht enthalten.
Installer werden nicht automatisch geloescht. Je nach Mediengroesse kann für
Download, Extraktion und fertiges Spiel mehr als die empfohlenen 100 GiB noetig sein.

## Referenzen

- [Arch-FS25-Container und dessen Silent-Setup](https://github.com/wine-gameservers/arch-fs25server)
- [Bestehendes Headless-Egg als Referenz für den Aktivierungsdialog und Portal-Ablauf](https://github.com/nn-home-com/farming-simulator-25-egg)

Die Adapter-Skripte in diesem Verzeichnis wurden für dieses Setup neu geschrieben.
Die veroeffentlichten Testaussagen des Referenzprojekts sind keine Tests dieses Adapters.
