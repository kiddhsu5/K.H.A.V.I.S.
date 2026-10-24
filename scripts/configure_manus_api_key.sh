#!/usr/bin/env bash
# Configure the Manus API bridge on the Tencent Cloud K.H.A.V.I.S. host.
# Secrets are read from the terminal, copied through a mode-600 temporary file,
# and never passed as process arguments.
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-ubuntu@43.156.115.110}"
SSH_KEY="${SSH_KEY:-$HOME/Documents/kiddhsu.pem}"
REMOTE_ENV="/home/ubuntu/.config/khavis/manus.env"
REMOTE_DROPIN_DIR="/etc/systemd/system/khavis-workbench.service.d"
REMOTE_DROPIN="${REMOTE_DROPIN_DIR}/10-manus-env.conf"

if [[ ! -r "$SSH_KEY" ]]; then
  echo "SSH key is not readable: $SSH_KEY" >&2
  exit 1
fi

read -r -s -p "Manus API Key: " MANUS_API_KEY
printf '\n' >&2
if [[ -z "$MANUS_API_KEY" || "$MANUS_API_KEY" == *$'\n'* || "$MANUS_API_KEY" == *$'\r'* ]]; then
  echo "Manus API Key cannot be empty or contain a newline." >&2
  exit 1
fi

read -r -s -p "K.H.A.V.I.S. Console Token (separate from Manus API Key): " KHAVIS_CONSOLE_TOKEN
printf '\n' >&2
if [[ -z "$KHAVIS_CONSOLE_TOKEN" || "$KHAVIS_CONSOLE_TOKEN" == *$'\n'* || "$KHAVIS_CONSOLE_TOKEN" == *$'\r'* ]]; then
  echo "Console Token cannot be empty or contain a newline." >&2
  exit 1
fi

umask 077
local_env="$(mktemp "${TMPDIR:-/tmp}/khavis-manus.XXXXXX")"
remote_tmp="/tmp/khavis-manus.${USER}.$$"
cleanup() {
  rm -f -- "$local_env"
}
trap cleanup EXIT

# printf %q makes the env file shell-safe without putting either value in argv.
printf 'MANUS_API_KEY=%q\nKHAVIS_CONSOLE_TOKEN=%q\n' \
  "$MANUS_API_KEY" "$KHAVIS_CONSOLE_TOKEN" >"$local_env"
unset MANUS_API_KEY KHAVIS_CONSOLE_TOKEN

scp -q -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" \
  "$local_env" "$REMOTE_HOST:$remote_tmp"
ssh -q -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" "$REMOTE_HOST" \
  "set -eu
   sudo install -d -o ubuntu -g ubuntu -m 700 /home/ubuntu/.config/khavis
   sudo install -o ubuntu -g ubuntu -m 600 '$remote_tmp' '$REMOTE_ENV'
   rm -f '$remote_tmp'
   sudo install -d -m 755 '$REMOTE_DROPIN_DIR'
   sudo install -o root -g root -m 644 /home/ubuntu/khavis/deploy/khavis-workbench-manus.conf '$REMOTE_DROPIN'
   sudo systemctl daemon-reload
   sudo systemctl restart khavis-workbench.service
   test \"\$(sudo systemctl is-active khavis-workbench.service)\" = active
   curl -fsS --max-time 10 http://127.0.0.1:8080/healthz >/dev/null"

echo "Manus bridge configured and khavis-workbench.service is active."
echo "Open http://43.156.115.110/workbench, enter the Console Token in the Manus console, and keep it out of URLs and chat messages."
