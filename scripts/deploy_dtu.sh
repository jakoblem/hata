#!/usr/bin/env bash
# Only for the *opt-in* GitHub Actions DTU deployment. Requires SSH access and
# a pre-created dedicated writable directory confirmed by DTU Compute IT.
set -euo pipefail

: "${DTU_SSH_HOST:?Set GitHub variable DTU_SSH_HOST}"
: "${DTU_SSH_USER:?Set GitHub variable DTU_SSH_USER}"
: "${DTU_WEB_ROOT:?Set GitHub variable DTU_WEB_ROOT}"
: "${DTU_SSH_PRIVATE_KEY:?Set GitHub secret DTU_SSH_PRIVATE_KEY}"
: "${DTU_SSH_KNOWN_HOSTS:?Set GitHub secret DTU_SSH_KNOWN_HOSTS with a VERIFIED server host key}"

# Disallow shell metacharacters in GitHub variables used in SSH commands.
[[ "$DTU_SSH_HOST" =~ ^[a-zA-Z0-9.-]+$ ]] || { echo 'Unsafe SSH host'; exit 2; }
[[ "$DTU_SSH_USER" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Unsafe SSH user'; exit 2; }
[[ "$DTU_WEB_ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo 'Use an absolute, simple web-root path'; exit 2; }
[[ "$DTU_WEB_ROOT" != / && "$DTU_WEB_ROOT" != /home && "$DTU_WEB_ROOT" != /var/www ]] || { echo 'Refusing broad unsafe rsync destination'; exit 2; }
port="${DTU_SSH_PORT:-22}"
[[ "$port" =~ ^[0-9]{1,5}$ ]] || { echo 'Invalid SSH port'; exit 2; }

umask 077
mkdir -p ~/.ssh
keyfile="$HOME/.ssh/id_hata_deploy"
printf '%s\n' "$DTU_SSH_PRIVATE_KEY" > "$keyfile"
printf '%s\n' "$DTU_SSH_KNOWN_HOSTS" > "$HOME/.ssh/known_hosts"
chmod 600 "$keyfile" "$HOME/.ssh/known_hosts"
trap 'rm -f "$keyfile"' EXIT
sshopt="ssh -i $keyfile -p $port -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15"

# Directory must already exist; never create unknown paths remotely.
$sshopt "${DTU_SSH_USER}@${DTU_SSH_HOST}" "test -d '${DTU_WEB_ROOT}' && test -w '${DTU_WEB_ROOT}'"
# WARNING: --delete removes files in the destination absent from site/.
# Only enable this when the directory is *dedicated solely to HATA*.
rsync -az --delete-delay --delay-updates -e "$sshopt" \
  site/ "${DTU_SSH_USER}@${DTU_SSH_HOST}:${DTU_WEB_ROOT%/}/"
echo "DTU static copy updated."
