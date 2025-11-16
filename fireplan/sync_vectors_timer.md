# Sync Vectors – Systemd Timer Setup

This document explains how to run the Django command `sync_vectors` every minute on the Raspberry Pi production server using a **systemd timer**.

---

## 1. Create the systemd service

Create:

`/etc/systemd/system/sync-vectors.service`

```ini
[Unit]
Description=Sync Vectors

[Service]
Type=oneshot
WorkingDirectory=/home/taqto/RadioAssetManagement/RadioAssetManagement
ExecStart=/home/taqto/RadioAssetManagement/bin/python manage.py sync_vectors
```

## 2. Create the systemd timer

Create:

`/etc/systemd/system/sync-vectors.timer`

```bash
[Unit]
Description=Run sync_vectors every minute

[Timer]
OnCalendar=*-*-* *:*:00
Persistent=true

[Install]
WantedBy=timers.target
```

## 3. Enable and start the timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sync-vectors.timer
```

## 4. Verify status

Check if the timer is active:

```bash
systemctl status sync-vectors.timer
```

Follow service logs:
```bash
journalctl -u sync-vectors.service -f
```