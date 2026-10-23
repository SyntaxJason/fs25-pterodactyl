# FS25 for Pterodactyl, without VNC

A custom PTDL_v2 egg and Pterodactyl adapter image for
[wine-gameservers/arch-fs25server](https://github.com/wine-gameservers/arch-fs25server).
It starts no VNC/noVNC, desktop or browser. Wine runs on an invisible Xvfb
display, and the online activation is done through the GIANTS dialog with xdotool.
The adapter image upgrades the Wine Staging 10.1 from the base image to
Wine 11.0 and adds matching Lavapipe/LLVM libraries.

## Quick start

1. Import `egg-farming-simulator-25.json` in the panel under Admin → Eggs.
2. Create a server with two allocations: the primary one is the game port
   (TCP and UDP, default 10825), the second one is `WEB_PORT` (TCP, default 7999).
3. Under Startup, set `WEB_PASSWORD` and `SERVER_ADMIN` (8–16 characters; GIANTS
   allows at most 16). Optionally set `FS25_PRODUCT_KEY`.
4. Start the server. Download, extraction, silent installation and first
   activation take a while on the first start; later starts reuse the files.

The egg uses the public image `ghcr.io/syntaxjason/fs25-pterodactyl:latest`
(linux/amd64, about 7.3 GB unpacked). Wings pulls it on the first start; users
do not need to build anything or run `install-wings.sh`. The image contains no
game files and no licenses.

## Keeping the web port private

The GIANTS web interface always listens on all interfaces inside the container, so
whether it is reachable from the internet is decided by the IP of the second
(`WEB_PORT`) allocation: Docker only publishes the port on that address.

- Use a loopback, Docker-bridge or private/VPN IP for the web allocation instead of
  the node's public IP. The game allocation stays public.
- Something internal then has to reach that address. With the BlueNet extension
  (1.0.45 or newer) set the node setting `fs25_dashboard_proxy` to `true`; the panel
  serves the dashboard itself, signs in with `WEB_USERNAME`/`WEB_PASSWORD` and the web
  port never needs to be public. See the extension's README.
- Without BlueNet, use your own reverse proxy or VPN in front of the web allocation.
  The interface is plain HTTP, so do not expose it directly.

## Product key

Set `FS25_PRODUCT_KEY` under Startup, or leave it empty. You need a separate
GIANTS dedicated server key.

- With the BlueNet extension (1.0.44 or newer), a popup asks for the key when the
  server starts without one. The key is entered masked and stored as a startup
  variable, then the waiting process restarts. Cancelling, closing the popup or
  an empty field stops the server. The popup is a BlueNet feature, not a generic
  feature of the egg.
- Without BlueNet, the container asks in the console. You have 60 seconds. No
  answer, an empty line, `abbrechen`/`cancel`/`stop` or a closed stdin stop the
  server cleanly (exit code 0) before Wine or a download starts. The panel
  console does not send empty commands; use `abbrechen` there or wait for the
  timeout. A console entry only applies to that start; set the key under Startup
  to keep it. Terminal echo is disabled during the prompt, but the panel command
  history may still store sent commands in the browser.

Pterodactyl stores startup variables in plain text in its database and passes
them on as container environment; server owners and administrators can see them.
The adapter does not write the key into the start command or its own console
messages and passes it to xdotool via stdin instead of argv.

To make an intentional stop stay stopped, Wings must respect clean exits. Set
`system.crash_detection.detect_clean_exit_as_crash: false` in the node's
`config.yml` (normal crash detection stays on with `enabled: true`). This
option applies to the whole node; see the
[Wings configuration](https://docs.pterodactyl.io/v2/wings/configuration#crash-detection).

## Game download

`AUTO_DOWNLOAD=true` registers your key at the official GIANTS portal and submits
the Windows IMG download form. The earlier direct CDN links are also supported.
An expired link or a changed portal page can be worked around by uploading the
installer manually: put the IMG/ZIP, or `Setup.exe` with all its BIN files, into
`installer/` and set `AUTO_DOWNLOAD=false`. No game files are shipped, and the
Steam installation of your PC is not used.

## Layout and persistence

- `.wine/`: Wine prefix and registry; not deleted on each start.
- `game/Farming Simulator 2025/`: installed game files.
- `config/FarmingSimulator2025/`: license files, mods, savegames and GIANTS configuration.
- `installer/`: uploaded/downloaded installation media; kept.
- `logs/`: installation, display, activation and process logs.

Both XML configurations are updated with an XML parser. Unknown settings, the
mod selection and the map of an existing world are preserved. Startup variables
for name, port, passwords and slot apply on every start. Change the map of an
existing configuration in the GIANTS portal; use `SAVEGAME_INDEX` for another
existing slot. The web credentials are written to the GIANTS `initial_admin`
block and initialise the first web user. Change an already created web user in
the GIANTS portal and update the egg variables accordingly.

The game is started by `dedicatedServer.exe` and an authenticated HTTP POST to
the GIANTS web interface. Only a new gameplay message in the game logs produces
`FS25_READY:` and thereby the Pterodactyl status "Running"; an early
"Started network game" does not count as a finished map start. The server logs,
including the dated `log_*.txt` engine logs, are streamed to the console.

A normal stop (`SIGINT`/`SIGTERM`) asks the GIANTS portal to stop the game
session and waits up to 45 seconds before Wine is terminated, so give the
container at least 60 seconds of stop timeout. The stop does not request an
additional manual world save; progress relies on GIANTS autosaves and manual
saving in the game. `SERVER_SAVE_INTERVAL` is measured in **minutes**
(default **3**).

## Image and CI

The image is built by GitHub Actions (`.github/workflows/image.yml`) and
published to GHCR. After each push the workflow checks that the image can be
pulled without logging in. GHCR packages are private on first publication; make
the package public once under Package settings.

To build locally for development and regenerate the egg:

```bash
docker build -t fs25-pterodactyl:local .
python3 build-egg.py
```

`install-wings.sh` builds and checks `fs25-pterodactyl:local` on a Wings host and
is only needed for local development.

The egg uses the PTDL_v2 format; see the
[egg documentation](https://docs.pterodactyl.io/v2/guides/egg-creation/creating-custom-egg).
The primary game port variable `SERVER_PORT` is provided by Wings and is not an
editable egg field.

## Limits

Verified locally with **FS25 1.25.0.0**: real GIANTS download, extraction, silent
installation, automatic online activation, game start up to "Entered Gameplay",
stop through GIANTS and restart with the existing activation. The activation
automation follows the ESD launcher with a 1280×720 display and supports its
title with build number; other GIANTS dialog layouts may need adjustments. A
timeout is reported as an error. Not tested: a connection with a real FS25 client,
and saving/restoring real client progress.

Automatic DLC installation and automatic game updates are not included.
Installers are not deleted automatically. Depending on the media size, more than
the recommended 100 GiB may be needed for download, extraction and the installed game.

## References

- [Arch FS25 container and its silent setup](https://github.com/wine-gameservers/arch-fs25server)
- [Existing headless egg, used as a reference for the activation dialog and portal flow](https://github.com/nn-home-com/farming-simulator-25-egg)

The adapter scripts in this repository were written anew for this setup.
