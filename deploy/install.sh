#!/usr/bin/env bash
# =============================================================================
# XZX verification bot - single-file VPS installer (Ubuntu).
#
# Moves the bot off Railway onto your OVH VPS. One file does everything: it
# installs deps, makes the service user, clones the code, builds the venv, and
# writes the .env template, the systemd service and the nginx config itself.
#
#   Install / redeploy:   curl -fsSL https://raw.githubusercontent.com/relievlng/verification-bot/main/deploy/install.sh | bash
#   Print the full guide: bash install.sh guide
#
# Idempotent - safe to re-run. It never touches your secrets, DNS or SSL; those
# are the manual steps it prints at the end (and in `install.sh guide`).
# =============================================================================
set -euo pipefail

REPO="https://github.com/relievlng/verification-bot.git"
APP_DIR="/opt/xzx-bot"
DATA_DIR="$APP_DIR/data"
SVC_USER="xzxbot"
DOMAIN="api.xzxsuite.com"          # change if the bot's public URL differs
PORT="8080"                         # change if the gang bot uses 8080 too

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- full guide --
guide() {
cat <<'GUIDE'
Moving the XZX bot from Railway to the OVH VPS
==============================================
Order matters. Nothing here touches Railway until the last step, so you can test
on the VPS while the old host keeps running.

0. Have ready: the VPS (Ubuntu, SSH, ufw, fail2ban - done), a domain for the
   bot's web server (your loader expects api.xzxsuite.com, reuse it), and the
   Railway env var values (token, Stripe secret, client id/secret).

1. Run this script on the VPS (installs everything, clones to /opt/xzx-bot):
     curl -fsSL https://raw.githubusercontent.com/relievlng/verification-bot/main/deploy/install.sh | bash

2. Move your data off Railway (licenses, tickets, config, files). From a shell
   with the Railway CLI (check your DB_PATH/FILES_DIR parent, e.g. /data):
     railway link
     railway ssh "tar czf - /data" > railway-data.tgz
     scp railway-data.tgz you@vps:/tmp/
     sudo tar xzf /tmp/railway-data.tgz -C /opt/xzx-bot/data --strip-components=1
     sudo chown -R xzxbot:xzxbot /opt/xzx-bot/data
   Fresh start with no data? Skip this; the bot makes an empty DB on boot.

3. Secrets:
     sudo -u xzxbot nano /opt/xzx-bot/.env      # fill tokens, Stripe, PUBLIC_URL
     sudo chmod 600 /opt/xzx-bot/.env

4. Start it:
     sudo systemctl start xzx-bot
     journalctl -u xzx-bot -f                   # expect "Logged in as ..."

5. Public endpoint. Point api.xzxsuite.com DNS (A record) at the VPS IP, wait
   for dig +short to show it, then:
     sudo ln -sf /etc/nginx/sites-available/xzx-bot /etc/nginx/sites-enabled/xzx-bot
     sudo nginx -t && sudo systemctl reload nginx
     sudo ufw allow 'Nginx Full'
     sudo apt-get install -y certbot python3-certbot-nginx
     sudo certbot --nginx -d api.xzxsuite.com
     curl https://api.xzxsuite.com/health        # -> ok

6. Repoint: Stripe webhook URL -> https://api.xzxsuite.com/stripe/webhook; the
   loader already uses api.xzxsuite.com so DNS alone moves it.

7. Cut over: once the VPS is healthy, pause/stop the Railway deployment. Keep the
   project a few days as rollback, then delete.

Redeploy after a code change:  re-run this script, or
   sudo git -C /opt/xzx-bot pull --ff-only && sudo systemctl restart xzx-bot
Gang bot (tenshi): same pattern, own user/dir/.env/service and a different PORT.
GUIDE
}

[ "${1:-}" = "guide" ] && { guide; exit 0; }

# ------------------------------------------------------------------ install --
say "Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git nginx

say "Creating service user '$SVC_USER'"
id "$SVC_USER" &>/dev/null || sudo useradd --system --create-home --shell /usr/sbin/nologin "$SVC_USER"

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

say "Writing the .env template (if absent)"
if [ ! -f "$APP_DIR/.env" ]; then
    sudo tee "$APP_DIR/.env" >/dev/null <<ENV
# Fill these in, then: sudo chmod 600 $APP_DIR/.env
DISCORD_TOKEN=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
STRIPE_WEBHOOK_SECRET=
PUBLIC_URL=https://$DOMAIN
XZX_API_BASE=https://$DOMAIN
DB_PATH=$DATA_DIR/verification.db
FILES_DIR=$DATA_DIR/files
PORT=$PORT
EMBED_THEME=black
LICENSE_PREFIX=XZX
DISCORD_INVITE=discord.gg/xzxx
# Optional: ALLOWED_GUILD_IDS, GUILD_ID, MESSAGE_CONTENT, FILE_STORAGE_MB,
# MAX_FILE_MB, STRIPE_EXTRA_HOSTS
ENV
    sudo chmod 600 "$APP_DIR/.env"
fi

say "Setting ownership"
sudo chown -R "$SVC_USER:$SVC_USER" "$APP_DIR"

say "Installing the systemd service"
sudo tee /etc/systemd/system/xzx-bot.service >/dev/null <<SERVICE
[Unit]
Description=XZX verification bot (Discord bot + web API)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SVC_USER
Group=$SVC_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=xzx-bot
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true
ReadWritePaths=$DATA_DIR

[Install]
WantedBy=multi-user.target
SERVICE
sudo systemctl daemon-reload
sudo systemctl enable xzx-bot

say "Writing the nginx reverse proxy (HTTPS added later by certbot)"
sudo tee /etc/nginx/sites-available/xzx-bot >/dev/null <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    client_max_body_size 25m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_request_buffering off;   # Stripe verifies the exact raw body
        proxy_buffering off;           # stream large downloads
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
NGINX

cat <<NEXT

==> Base install done. Finish the manual steps (full details: bash install.sh guide):

  1. Data:   copy verification.db + files/ from Railway into $DATA_DIR
             (railway ssh "tar czf - /data" > ... then unpack), then
             sudo chown -R $SVC_USER:$SVC_USER $DATA_DIR
  2. Secrets: sudo -u $SVC_USER nano $APP_DIR/.env   (fill tokens, Stripe)
  3. Start:  sudo systemctl start xzx-bot && journalctl -u xzx-bot -f
  4. Web:    point $DOMAIN DNS at this VPS, then
             sudo ln -sf /etc/nginx/sites-available/xzx-bot /etc/nginx/sites-enabled/xzx-bot
             sudo nginx -t && sudo systemctl reload nginx && sudo ufw allow 'Nginx Full'
             sudo certbot --nginx -d $DOMAIN
  5. Stripe: set the webhook URL to https://$DOMAIN/stripe/webhook

NEXT
