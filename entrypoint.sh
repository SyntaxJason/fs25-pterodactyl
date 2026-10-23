#!/bin/bash
set -euo pipefail
# Wings startet den Container mit der UID/GID des Hosts (z. B. 999 statt 988).
# Wine und Python brauchen dafür einen passwd-Eintrag; der Nutzer heißt weiter
# "container", damit bestehende Wine-Profile passen.
uid="$(id -u)"; gid="$(id -g)"
if [ "$uid" != 0 ] && ! getent passwd "$uid" >/dev/null; then
    sed "s/^container:x:[0-9]*:[0-9]*:/container:x:${uid}:${gid}:/" /etc/passwd > /tmp/passwd.new
    cat /tmp/passwd.new > /etc/passwd; rm -f /tmp/passwd.new
fi
if [ "$uid" != 0 ] && ! getent group "$gid" >/dev/null; then
    echo "ptero:x:${gid}:" >> /etc/group
fi
cd /home/container
exec bash -c "${STARTUP:-exec python /opt/fs25-ptero/runtime.py}"
