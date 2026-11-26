#!/usr/bin/env bash
# One-shot VPS setup for the XZX verification bot (Ubuntu). Idempotent: safe to
# re-run. Run as a user with sudo on the OVH VPS:
#     curl -fsSL https://raw.githubusercontent.com/relievlng/verification-bot/main/deploy/setup.sh | bash
# or clone first and run: bash deploy/setup.sh
#
# It installs deps, creates the xzxbot service user, clones the repo to
# /opt/xzx-bot, builds the venv, and installs the systemd service. It does NOT
# touch secrets, DNS, nginx or SSL - those are the manual steps in MIGRATION.md.
set -euo pipefail

REPO="https://github.com/relievlng/verification-bot.git"
APP_DIR="/opt/xzx-bot"
DATA_DIR="$APP_DIR/data"
SVC_USER="xzxbot"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

say "Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git nginx

say "Creating service user '$SVC_USER'"
if ! id "$SVC_USER" &>/dev/null; then
    sudo useradd --system --create-home --shell /usr/sbin/nologin "$SVC_USER"
fi

say "Fetching the code into $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    sudo git -C "$APP_DIR" pull --ff-only
else
    sudo git clone "$REPO" "$APP_DIR"
fi
sudo mkdir -p "$DATA_DIR/files"

say "Building the Python environment"
sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

say "Setting ownership"
sudo chown -R "$SVC_USER:$SVC_USER" "$APP_DIR"

say "Installing the systemd service"
sudo cp "$APP_DIR/deploy/xzx-bot.service" /etc/systemd/system/xzx-bot.service
sudo systemctl daemon-reload
sudo systemctl enable xzx-bot

cat <<'NEXT'

==> Base setup done. Before starting the bot, finish the manual steps:

  1. Secrets:   sudo -u xzxbot cp /opt/xzx-bot/.env.example /opt/xzx-bot/.env
                sudo -u xzxbot nano /opt/xzx-bot/.env         # fill in tokens
                sudo chmod 600 /opt/xzx-bot/.env
  2. Data:      copy your existing verification.db + files/ from Railway into
                /opt/xzx-bot/data/   (see MIGRATION.md "Move your data")
                sudo chown -R xzxbot:xzxbot /opt/xzx-bot/data
  3. Start:     sudo systemctl start xzx-bot
                journalctl -u xzx-bot -f          # watch it boot
  4. Web/SSL:   set up nginx + certbot for your domain (see MIGRATION.md)

NEXT
say "See /opt/xzx-bot/deploy/MIGRATION.md for the full walkthrough."
