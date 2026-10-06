#!/usr/bin/env bash
set -euo pipefail

for name in EC2_HOST EC2_USER EC2_SSH_KEY EC2_KNOWN_HOSTS; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required GitHub Actions secret: %s\n' "$name" >&2
    exit 1
  fi
done

# These values go into an SSH config; reject whitespace and config directives.
[[ "$EC2_HOST" =~ ^[a-zA-Z0-9][a-zA-Z0-9.:-]*$ ]] || { echo "Invalid EC2_HOST" >&2; exit 1; }
[[ "$EC2_USER" =~ ^[a-zA-Z_][a-zA-Z0-9_-]*$ ]] || { echo "Invalid EC2_USER" >&2; exit 1; }
EC2_PORT="${EC2_PORT:-22}"
[[ "$EC2_PORT" =~ ^[0-9]{1,5}$ ]] && ((10#$EC2_PORT >= 1 && 10#$EC2_PORT <= 65535)) || {
  echo "EC2_PORT must be a port number from 1 to 65535" >&2
  exit 1
}
EC2_PORT=$((10#$EC2_PORT))

for file in index.html models/cusat.glb models/cusat-mobile.glb campus-poster.webp; do
  [[ -s "dist/$file" ]] || { echo "Missing build file: dist/$file. Run npm run build first." >&2; exit 1; }
done
command -v ssh >/dev/null
command -v ssh-keygen >/dev/null
command -v rsync >/dev/null

deploy_path=/var/www/dhishna.org
umask 077
ssh_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/dhishna-ssh.XXXXXX")
trap 'rm -rf -- "$ssh_dir"' EXIT
printf '%s\n' "$EC2_SSH_KEY" | tr -d '\r' > "$ssh_dir/key"
printf '%s\n' "$EC2_KNOWN_HOSTS" | tr -d '\r' > "$ssh_dir/known_hosts"
unset EC2_SSH_KEY EC2_KNOWN_HOSTS

# Validate the entry using the same host/port lookup as OpenSSH, including
# hashed known_hosts entries. Never fetch or silently trust a replacement key.
host_lookup="$EC2_HOST"
if ((EC2_PORT != 22)); then
  host_lookup="[$EC2_HOST]:$EC2_PORT"
fi
if ! ssh-keygen -F "$host_lookup" -f "$ssh_dir/known_hosts" > "$ssh_dir/matching_hosts" 2>/dev/null; then
  echo "EC2_KNOWN_HOSTS has no entry matching EC2_HOST and EC2_PORT." >&2
  printf 'Expected entry format: %s KEY_TYPE BASE64_PUBLIC_HOST_KEY\n' "$host_lookup" >&2
  echo "Paste the complete verified host-key line, without quotes, a shell prompt, or a SHA256 fingerprint." >&2
  exit 1
fi
if ! ssh-keygen -lf "$ssh_dir/matching_hosts" -E sha256 >/dev/null 2>&1; then
  echo "EC2_KNOWN_HOSTS matches the host and port but contains no valid public key." >&2
  echo "Use the complete key type and base64 key from the server's public host-key file, not its SHA256 fingerprint." >&2
  exit 1
fi

cat > "$ssh_dir/config" <<EOF
Host dhishna-deploy
    HostName $EC2_HOST
    User $EC2_USER
    Port $EC2_PORT
    IdentityFile "$ssh_dir/key"
    IdentitiesOnly yes
    BatchMode yes
    StrictHostKeyChecking yes
    UserKnownHostsFile "$ssh_dir/known_hosts"
    ConnectTimeout 15
    ServerAliveInterval 15
    ServerAliveCountMax 4
EOF

# The server's existing web root must be writable by the deployment user.
ssh -F "$ssh_dir/config" dhishna-deploy \
  "test -d '$deploy_path' && test -w '$deploy_path' && command -v rsync >/dev/null"

# Retain old hashed assets for visitors who already loaded an earlier page.
# Never delete unrelated server files or transfer a local dist/.git directory.
rsync_flags=(-rptz --checksum --delay-updates --omit-dir-times --chmod=D755,F644 --timeout=120
  --rsh "ssh -F '$ssh_dir/config'")
rsync "${rsync_flags[@]}" --exclude=/index.html --exclude=/.git/ \
  dist/ "dhishna-deploy:$deploy_path/"

# Publish the entry page only after every other upload has succeeded.
rsync "${rsync_flags[@]}" dist/index.html "dhishna-deploy:$deploy_path/"
echo "Deployed dist/ to $deploy_path"
