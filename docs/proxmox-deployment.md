# Proxmox deployment

This guide deploys Daymark in a dedicated Debian VM on Proxmox VE using Docker Compose. A VM keeps Docker and application updates separate from the Proxmox host. Do not install the application or Docker Engine on the Proxmox host.

## 1. Create and secure the VM

Create a Debian 13 VM with a VirtIO network adapter and a disk on storage included in your Proxmox backup plan. As a starting point, allocate 2 vCPU and 4 GiB RAM; allow more memory and CPU if an Ollama model runs in the VM. Give the guest a DHCP reservation or static address, enable the QEMU guest agent, and apply Debian security updates.

Keep the guest on a trusted LAN or VPN. The Compose frontend publishes only on the VM loopback interface (`127.0.0.1:3000`); the backend has no host-published port. Do not change that binding to `0.0.0.0`. Authentication is not implemented. Before access from other machines, put an HTTPS reverse proxy with authentication in front of the frontend and restrict firewall access to trusted clients. Do not expose the app or Ollama to the public internet.

## 2. Install Docker and the application

Install Docker Engine and the Compose plugin in the Debian guest using Docker's official Debian instructions. Create a dedicated non-root deployment account, add it to the Docker group (which grants root-equivalent control of that VM), and install Git:

```sh
sudo apt update
sudo apt install -y ca-certificates curl git
```

Create `/opt/daymark` for the deployment account, then clone the repository there and run Compose from that directory:

```sh
sudo install -d -o daymark -g daymark /opt/daymark
sudo -u daymark git clone https://github.com/ebldx/dashboard.git /opt/daymark
sudo -u daymark -H sh -c 'cd /opt/daymark && cp .env.example .env'
cd /opt/daymark
```

Generate a unique Fernet key and set it as `CALENDAR_ENCRYPTION_KEY` in `.env`:

```sh
docker compose run --rm --no-deps api python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Store `.env` with restrictive permissions (`chmod 600 .env`). Back up the calendar encryption key separately in a secure password manager; the database backup does not include `.env` or encryption keys. Losing the key makes saved calendar feed URLs unrecoverable.

Optionally set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` to an Ollama service on a trusted private network. Ollama is not included in this Compose project. Then start the app and confirm its health:

```sh
docker compose up --build -d
docker compose ps
curl --fail http://127.0.0.1:3000/api/system/health
```

## 3. Configure application backups and scheduled jobs

Mount backup archives to storage separate from the Compose data volume. For example, mount a NAS or a dedicated backup disk at `/mnt/daymark-backups`, then add this to `/opt/daymark/.env`:

```dotenv
BACKUP_DIR=/mnt/daymark-backups
```

The Compose API service mounts that location at `/backups`. Ensure the filesystem is mounted before enabling the timer; otherwise Docker may create the directory on the VM's root disk. For a systemd-managed mount, add a dependency to the backup service with `sudo systemctl edit daymark-docker-backup.service`:

```ini
[Unit]
RequiresMountsFor=/mnt/daymark-backups
```

Archives include a consistent SQLite snapshot, uploaded CV files, and a SHA-256 manifest. They are private ZIP files, retained locally at 14 by default. They do not include `.env`, secrets, or the encryption key. Store an encrypted copy off the VM; a Proxmox VM backup and an application backup have different recovery purposes.

Install the Docker-compatible systemd units and enable daily briefing, retry, weekly review, and backup timers:

```sh
sudo install -m 0644 deploy/systemd/daymark-docker-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now \
  daymark-docker-daily-briefing.timer \
  daymark-docker-daily-retry.timer \
  daymark-docker-weekly-review.timer \
  daymark-docker-weekly-retry.timer \
  daymark-docker-backup.timer
```

Set the guest timezone to Europe/Oslo for the configured schedule with `sudo timedatectl set-timezone Europe/Oslo`. Inspect timers and logs with `systemctl list-timers 'daymark-docker-*'` and `journalctl -u daymark-docker-backup.service`. The systemd units invoke Docker Compose and therefore need access to the Docker socket; treat that privilege as root-equivalent.

Create a backup manually and verify the newest archive:

```sh
docker compose run --rm --no-deps api python -m app.backup /backups --keep 14
BACKUP_FILE="$(find /mnt/daymark-backups -maxdepth 1 -name 'daymark-backup-*.zip' -type f -printf '%f\n' | sort | tail -n 1)"
docker compose run --rm --no-deps api python -m app.backup --verify "/backups/$BACKUP_FILE"
```

Keep copies of the archive and `.env` encryption key in separate protected locations. Periodically test recovery in an isolated VM: stop the app, verify the archive, extract it to a staging directory, restore `database/dashboard.db` to the configured SQLite database path and the archive's `files/` contents to `FILE_STORAGE_DIR`, then start the app and check its health. Never test restore over the only production copy.

## 4. Proxmox backup and recovery

Configure Proxmox Backup Server or scheduled `vzdump` backups for the VM, with retention and off-host storage appropriate to your recovery objectives. A VM snapshot alone is not a substitute for the application archive and does not back up the `.env` key safely. Protect guest and archive backups as sensitive personal data.

After restoring a VM backup, check `docker compose ps`, the API health endpoint, the frontend, and the systemd timers. If restoring an application archive to a clean VM, restore the separately stored `.env` first, start the Compose services, then check database and uploaded-file availability. Keep the application and Proxmox management interfaces on trusted networks; do not port-forward either from the internet.

## Limitations

- Authentication and user accounts are not implemented; network isolation or an authenticated HTTPS proxy is required.
- Application archives support file-based SQLite only. They are not encrypted; use encrypted storage or encrypt them before sending off-host.
- Restore is a documented operator procedure, not an automated destructive command.
- Ollama is optional and should be isolated from untrusted networks.
