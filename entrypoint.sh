#!/bin/bash
set -euo pipefail
cd /home/container
exec bash -c "${STARTUP:-exec python /opt/fs25-ptero/runtime.py}"
