import os
import pwd
import re
import select
import signal
import socket
import subprocess
import sys
import termios
import time
from pathlib import Path

from configure import configure
from download import download
from portal import Portal

ROOT = Path('/home/container')
GAME = ROOT / 'game' / 'Farming Simulator 2025'
PROFILE = ROOT / 'config' / 'FarmingSimulator2025'
PREFIX = ROOT / '.wine'
INSTALLER = ROOT / 'installer'
LOGS = ROOT / 'logs'
CHILDREN = []
STOPPING = False
portal = None


def redact(value):
    for key in ('FS25_PRODUCT_KEY', 'WEB_PASSWORD', 'SERVER_ADMIN', 'SERVER_PASSWORD'):
        secret = os.environ.get(key, '')
        if secret:
            value = value.replace(secret, '[REDACTED]')
            if key == 'FS25_PRODUCT_KEY':
                value = value.replace(re.sub(r'[\s-]', '', secret), '[REDACTED]')
    return value


def log(value):
    print('[FS25] ' + redact(str(value)), flush=True)


def launch(args, name):
    with (LOGS / name).open('ab', buffering=0) as output:
        try:
            process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT)
        except FileNotFoundError:
            raise RuntimeError(f'Required runtime program is missing: {args[0]}. Rebuild the Docker image.') from None
    CHILDREN.append(process)
    return process


def run(args, name, timeout=300):
    process = launch(args, name)
    try:
        if process.wait(timeout=timeout):
            raise RuntimeError(f'{name} failed; inspect logs/{name}.')
    except subprocess.TimeoutExpired:
        process.terminate()
        raise RuntimeError(f'{name} timed out; inspect logs/{name}.') from None


def wine_stop():
    subprocess.run(['wineserver', '-k'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    try:
        subprocess.run(['wineserver', '-w'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    except subprocess.TimeoutExpired:
        pass


def cleanup():
    try:
        wine_stop()
    except (OSError, subprocess.TimeoutExpired):
        pass
    for process in reversed(CHILDREN):
        if process.poll() is None:
            process.terminate()
    for process in reversed(CHILDREN):
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


def shutdown(signum, frame):
    global STOPPING
    if STOPPING:
        return
    STOPPING = True
    log('Stop requested. Asking GIANTS to stop the game session.')
    if portal is not None:
        try:
            portal.stop()
            until = time.monotonic() + 45
            while time.monotonic() < until:
                form = portal.form()
                if 'start_server' in form.buttons and 'stop_server' not in form.buttons:
                    log('GIANTS game session stopped.')
                    break
                time.sleep(2)
            else:
                log('GIANTS stop timed out after 45 seconds; closing Wine.')
        except Exception:
            log('GIANTS portal unavailable during stop; closing Wine.')
    raise SystemExit(0)


def link(target, location):
    location.parent.mkdir(parents=True, exist_ok=True)
    if location.is_symlink():
        if location.resolve() != target.resolve():
            raise RuntimeError(f'Unexpected existing symlink: {location}')
        return
    if location.exists():
        if location.is_dir() and not any(location.iterdir()):
            location.rmdir()
        else:
            raise RuntimeError(f'Existing data at {location}; move it into {target} before starting.')
    location.symlink_to(target, target_is_directory=True)


def setup_display():
    display = launch(['Xvfb', ':99', '-screen', '0', '1280x720x24', '-nolisten', 'tcp', '-ac'], 'display.log')
    for _ in range(100):
        if display.poll() is not None:
            raise RuntimeError('Virtual display exited; inspect logs/display.log.')
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.connect('/tmp/.X11-unix/X99')
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError('Virtual display failed to start.')


def setup_prefix():
    if not (PREFIX / 'system.reg').is_file():
        log('Creating persistent Wine prefix (first start).')
        run(['wineboot', '--init'], 'wineboot.log', 180)
        run(['wineserver', '-w'], 'wineboot.log', 90)
    username = pwd.getpwuid(os.getuid()).pw_name
    user = PREFIX / 'drive_c' / 'users' / username
    documents = user / 'Documents'
    # Wine can map Documents onto $HOME; replace only that generated link.
    if documents.is_symlink():
        documents.unlink()
    documents.mkdir(parents=True, exist_ok=True)
    link(PROFILE, documents / 'My Games' / 'FarmingSimulator2025')
    link(GAME, PREFIX / 'drive_c' / 'Program Files (x86)' / 'Farming Simulator 2025')


def installer_exe():
    matches = [p for p in INSTALLER.rglob('*') if p.is_file() and p.name.lower() == 'setup.exe']
    if not matches:
        matches = [p for p in INSTALLER.rglob('*') if p.is_file() and p.name.lower() == 'farmingsimulator2025.exe']
    if len(matches) > 1:
        raise RuntimeError('Multiple setup executables in installer/. Keep one installer version.')
    return matches[0] if matches else None


def install():
    if (GAME / 'dedicatedServer.exe').is_file() and (GAME / 'FarmingSimulator2025.exe').is_file():
        log('Existing game installation found.')
        return
    setup = installer_exe()
    if setup is None:
        archives = [p for p in INSTALLER.iterdir() if p.suffix.lower() in ('.img', '.zip')]
        if not archives and os.environ.get('AUTO_DOWNLOAD', 'true') == 'true':
            archives = [download(INSTALLER, os.environ['FS25_PRODUCT_KEY'], log)]
            if archives[0].suffix.lower() == '.exe':
                setup = archives[0]
                archives = []
        if len(archives) > 1:
            raise RuntimeError('Multiple archives in installer/. Keep one installer version.')
        if archives:
            log('Extracting GIANTS installation media.')
            run(['7z', 'x', str(archives[0]), '-o' + str(INSTALLER), '-y', '-bso0', '-bsp0'], 'extract.log', 1800)
            setup = installer_exe()
    if setup is None:
        raise RuntimeError('FS25 installer missing. Upload GIANTS IMG/ZIP/Setup.exe + BIN files into installer/, or enable AUTO_DOWNLOAD.')
    log('Installing FS25 silently. Progress is recorded in logs/install.log.')
    run(['wine', str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NOCANCEL', '/NOICONS', '/NORESTART',
         r'/DIR=C:\Program Files (x86)\Farming Simulator 2025'], 'install.log', 3600)
    if not (GAME / 'dedicatedServer.exe').is_file() or not (GAME / 'FarmingSimulator2025.exe').is_file():
        raise RuntimeError('Installer finished without the expected game files; inspect logs/install.log.')
    log('FS25 installation complete.')


def activate():
    # Empty files must never count as successful activation.
    def licensed():
        return any(p.stat().st_size > 0 for p in PROFILE.glob('*.dat'))
    if licensed():
        log('Persistent license files found; skipping activation.')
        return
    log('Opening the GIANTS activation dialog on the hidden display.')
    launcher = launch(['wine', str(GAME / 'FarmingSimulator2025.exe')], 'activation.log')
    deadline = time.monotonic() + int(os.environ.get('ACTIVATION_TIMEOUT', '180'))
    entered = False
    while time.monotonic() < deadline:
        if licensed():
            wine_stop()
            log('GIANTS activation produced license files.')
            return
        if launcher.poll() is not None:
            raise RuntimeError('GIANTS activation launcher exited without license files; inspect logs/activation.log.')
        if not entered:
            found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', '^FarmingSimulator2025([[:space:]]|$)'],
                                   capture_output=True, text=True)
            if found.returncode == 0:
                window = found.stdout.splitlines()[-1]
                # This layout follows the FS25 ESD launcher at 1280x720 without a WM.
                # Feed the serial over stdin, never as a process argument.
                time.sleep(3)
                subprocess.run(['xdotool', 'windowfocus', '--sync', window], check=True, timeout=10)
                subprocess.run(['xdotool', 'mousemove', '746', '361', 'click', '1', 'key', '--clearmodifiers', 'ctrl+a', 'Delete'], check=True)
                key = re.sub(r'[\s-]', '', os.environ['FS25_PRODUCT_KEY'])
                subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '60', '--file', '-'], input=key, text=True, check=True)
                time.sleep(1)
                subprocess.run(['xdotool', 'mousemove', '875', '536', 'click', '1'], check=True)
                entered = True
                log('Product key submitted to GIANTS; waiting for activation.')
        time.sleep(2)
    raise RuntimeError('GIANTS activation timed out. Check the key, internet access and logs/activation.log. The dialog layout may differ with this installer version.')


def log_paths():
    return [PROFILE / 'log.txt', *sorted(PROFILE.glob('log_*.txt')),
            *sorted((PROFILE / 'dedicated_server' / 'logs').glob('*.log'))]


def stream_logs(offsets):
    ready = False
    paths = log_paths()
    for path in paths:
        if not path.is_file():
            continue
        offset = offsets.get(path, 0)
        if path.stat().st_size < offset:
            offset = 0
        with path.open('rb') as source:
            source.seek(offset)
            while line := source.readline():
                if not line.endswith(b'\n'):
                    source.seek(source.tell() - len(line))
                    break
                text = line.decode('utf-8', errors='replace').rstrip()
                log(text)
                if 'Entered Gameplay' in text:
                    ready = True
            offsets[path] = source.tell()
    return ready


def require_product_key(timeout=60):
    if os.environ.get('FS25_PRODUCT_KEY', '').strip():
        return

    log(f'FS25_LICENSE_REQUIRED: Kein License Key gesetzt. GIANTS-Key innerhalb von {timeout} Sekunden in der Konsole eingeben.')
    log('Ohne Eingabe wird der Server gestoppt. Mit "abbrechen" sofort stoppen. Dauerhaft: Startup > FS25_PRODUCT_KEY.')
    descriptor = sys.stdin.fileno()
    previous = None
    try:
        if os.isatty(descriptor):
            previous = termios.tcgetattr(descriptor)
            hidden = previous.copy()
            hidden[3] &= ~(termios.ECHO | termios.ECHONL)
            termios.tcsetattr(descriptor, termios.TCSANOW, hidden)
        deadline = time.monotonic() + timeout
        pending = b''
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([descriptor], [], [], max(0, remaining))[0]:
                log('Kein License Key eingegeben (Timeout). Server wird gestoppt.')
                raise SystemExit(0)
            chunk = os.read(descriptor, 256)
            if not chunk:
                log('Keine Eingabe verfuegbar. Server wird gestoppt.')
                raise SystemExit(0)
            pending += chunk
            if len(pending) > 256:
                raise RuntimeError('License Key input is too long. Set a valid key in Startup > FS25_PRODUCT_KEY.')
            if b'\n' in pending or b'\r' in pending:
                key = pending.splitlines()[0].decode('utf-8', errors='replace').strip()
                if not key or key.casefold() in ('abbrechen', 'cancel', 'stop', 'exit'):
                    log('Kein License Key angegeben. Server wird gestoppt.')
                    raise SystemExit(0)
                os.environ['FS25_PRODUCT_KEY'] = key
                log('License Key uebernommen; Download und Aktivierung werden vorbereitet.')
                return
    finally:
        if previous is not None:
            termios.tcsetattr(descriptor, termios.TCSANOW, previous)


def main():
    global portal
    os.umask(0o077)
    os.environ.update(WINEPREFIX=str(PREFIX), WINEARCH='win64', WINEDEBUG='-all',
                      WINEDLLOVERRIDES='mscoree=d;mshtml=d', DISPLAY=':99')
    for directory in (GAME, PROFILE, INSTALLER, LOGS):
        directory.mkdir(parents=True, exist_ok=True)
    require_product_key()
    for variable in ('WEB_PASSWORD', 'SERVER_ADMIN', 'SERVER_PORT'):
        if not os.environ.get(variable, '').strip():
            raise RuntimeError(f'Required egg variable is empty: {variable}')
    if os.environ['FS25_PRODUCT_KEY'] == 'TEST0-TEST0-TEST0-TEST0':
        raise RuntimeError('Replace the test placeholder in Startup > FS25_PRODUCT_KEY with your GIANTS server key.')
    if not re.fullmatch(r'[A-Za-z0-9]{20,40}', re.sub(r'[\s-]', '', os.environ['FS25_PRODUCT_KEY'])):
        raise RuntimeError('FS25_PRODUCT_KEY must contain a GIANTS product key (20-64 characters, letters/digits/dashes).')
    if os.environ.get('WEB_PORT', '7999') == os.environ['SERVER_PORT']:
        raise RuntimeError('WEB_PORT must differ from the primary game allocation.')
    setup_display()
    setup_prefix()
    install()
    activate()
    configure(GAME, PROFILE)
    port = os.environ.get('WEB_PORT', '7999')
    addresses = list(dict.fromkeys(socket.gethostbyname_ex(socket.gethostname())[2] + ['127.0.0.1']))
    offsets = {p: p.stat().st_size for p in log_paths() if p.is_file()}
    log('Launching GIANTS dedicatedServer.exe on the hidden Wine desktop.')
    launch(['wine', 'explorer', '/desktop=fs25,1280x720', str(GAME / 'dedicatedServer.exe')], 'dedicated-process.log')
    until = time.monotonic() + 180
    while time.monotonic() < until:
        for address in addresses:
            try:
                with socket.create_connection((address, int(port)), timeout=.5):
                    pass
                portal = Portal(address, port, os.environ.get('WEB_USERNAME', 'admin'), os.environ['WEB_PASSWORD'])
                break
            except OSError:
                continue
        if portal is not None:
            break
        time.sleep(1)
    if portal is None:
        raise RuntimeError('GIANTS web portal did not listen within 180 seconds. Inspect logs/dedicated-process.log.')
    portal.start()
    log(f'Game session start requested. Web administration uses allocation {port}/TCP.')
    ready = False
    deadline = time.monotonic() + int(os.environ.get('START_TIMEOUT', '300'))
    last_check = time.monotonic()
    while True:
        if stream_logs(offsets) and not ready:
            ready = True
            log('FS25_READY: game session entered gameplay.')
        if not ready and time.monotonic() > deadline:
            raise RuntimeError('Game session did not reach gameplay before START_TIMEOUT. Inspect config/FarmingSimulator2025/log*.txt and the GIANTS portal.')
        if time.monotonic() - last_check > 15:
            # Do not keep an apparently healthy container alive after the portal dies.
            with socket.create_connection((portal.host, portal.port), timeout=3):
                pass
            last_check = time.monotonic()
        time.sleep(1)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    code = 0
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        # URL/network errors can contain signed download links; don't print them.
        if isinstance(exc, (OSError, TimeoutError)):
            log(f'ERROR: {type(exc).__name__}; inspect the runtime logs and network settings.')
        else:
            log('ERROR: ' + str(exc))
        code = 1
    finally:
        cleanup()
    sys.exit(code)
