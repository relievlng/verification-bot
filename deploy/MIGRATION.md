# Moving the XZX bot from Railway to the OVH VPS

This walks the `verification-bot` from Railway onto your Ubuntu VPS: the bot
process, its SQLite database, uploaded files, and its public web endpoint
(`api.xzxsuite.com` - Stripe webhook, `/api/activate`, download links).

**Shape of it:** `python bot.py` runs under systemd and keeps itself alive. It
loads secrets from `/opt/xzx-bot/.env`. Its aiohttp web server listens on
`127.0.0.1:8080`; nginx sits in front with HTTPS and forwards your domain to it.
Data (the `.db` file and `files/`) lives in `/opt/xzx-bot/data`.

Do it in this order. Nothing here touches Railway until the last step, so you can
test on the VPS while the old host keeps running.

---

## 0. Before you start

- VPS ready (you have this): Ubuntu, key-based SSH, ufw, fail2ban.
- A domain/subdomain for the bot's web server. Your loader already expects
  `api.xzxsuite.com`, so reuse that - you'll just repoint its DNS at the end.
- The Railway service's env var values to hand (token, Stripe secret, client
  id/secret) - copy them from the Railway dashboard -> Variables.
- Railway CLI on your laptop if you want to script the data export:
  `npm i -g @railway/cli` then `railway login`.

## 1. Code + Python on the VPS

SSH in, then run the setup script (installs Python, nginx, git; makes the
`xzxbot` user; clones to `/opt/xzx-bot`; builds the venv; installs the service):

```bash
curl -fsSL https://raw.githubusercontent.com/relievlng/verification-bot/main/deploy/setup.sh | bash
```

Re-running it later just pulls the latest code and reinstalls deps - that's your
redeploy command too.

## 2. Move your data off Railway

Your licenses, tickets, config and uploaded files live in the SQLite DB and the
files dir on Railway's volume. Find their paths in Railway -> Variables
(`DB_PATH`, `FILES_DIR`). Then, from your laptop:

```bash
# Pull the whole data volume out of Railway (adjust the mount path to your
# DB_PATH/FILES_DIR parent, e.g. /data):
railway link                     # pick the verification-bot project
railway ssh "tar czf - /data" > railway-data.tgz

# Copy it to the VPS and unpack into the data dir:
scp railway-data.tgz you@your-vps:/tmp/
ssh you@your-vps
sudo tar xzf /tmp/railway-data.tgz -C /opt/xzx-bot/data --strip-components=1
sudo chown -R xzxbot:xzxbot /opt/xzx-bot/data
```

(No `railway ssh`? Use `railway run bash` to get a shell, `tar`/`base64` the data
and paste it out, or download the volume from the Railway dashboard.)

If this is a fresh start with no data to keep, skip this - the bot creates an
empty DB on first boot.

## 3. Secrets (.env)

```bash
sudo -u xzxbot cp /opt/xzx-bot/.env.example /opt/xzx-bot/.env
sudo -u xzxbot nano /opt/xzx-bot/.env
sudo chmod 600 /opt/xzx-bot/.env
```

Fill in `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`,
`STRIPE_WEBHOOK_SECRET`, and set `PUBLIC_URL=https://api.xzxsuite.com` and
`XZX_API_BASE=https://api.xzxsuite.com`. Leave `DB_PATH` and `FILES_DIR` at the
`/opt/xzx-bot/data/...` defaults so they match where you unpacked the data.

## 4. Start the bot

```bash
sudo systemctl start xzx-bot
journalctl -u xzx-bot -f
```

You want to see `Logged in as ...` and `Web server listening on port 8080`.
`Ctrl-C` stops the log tail (not the bot). The bot now runs and reconnects on
its own; it starts on boot too.

## 5. Public web endpoint (nginx + HTTPS)

Point your domain's DNS **A record** at the VPS IP first (`api.xzxsuite.com` ->
VPS IP), wait for it to resolve (`dig +short api.xzxsuite.com`), then:

```bash
sudo cp /opt/xzx-bot/deploy/nginx-xzx-bot.conf /etc/nginx/sites-available/xzx-bot
# edit the file if your domain isn't api.xzxsuite.com:
sudo nano /etc/nginx/sites-available/xzx-bot
sudo ln -sf /etc/nginx/sites-available/xzx-bot /etc/nginx/sites-enabled/xzx-bot
sudo nginx -t && sudo systemctl reload nginx

# open the firewall and get a certificate:
sudo ufw allow 'Nginx Full'
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.xzxsuite.com
```

certbot adds the HTTPS block and the HTTP->HTTPS redirect, and auto-renews.
Check: `curl https://api.xzxsuite.com/health` should return `ok`.

## 6. Repoint the integrations

- **DNS**: done in step 5 (`api.xzxsuite.com` -> VPS).
- **Stripe**: Dashboard -> Developers -> Webhooks -> your endpoint -> set the URL
  to `https://api.xzxsuite.com/stripe/webhook`. Confirm the signing secret in
  `.env` matches. Send a test event and watch `journalctl -u xzx-bot -f`.
- **Loader**: it already calls `XZX_API_BASE` (`api.xzxsuite.com`), so once DNS
  points at the VPS it hits the new backend with no client change.

## 7. Cut over

Run both hosts in parallel for a bit. Two Discord sessions for one bot token is
fine briefly, but to avoid double-posting, once the VPS looks healthy **stop the
Railway service** (Railway -> Settings -> pause/remove the deployment). Keep the
Railway project a few days as a rollback, then delete it.

---

## Running the gang bot (tenshi) on the same VPS

Repeat the pattern with its own user, dir (`/opt/tenshi`), `.env`, a second
systemd unit, and - if it also serves web - a **different** `PORT` (e.g. 8081)
and its own nginx server block/domain. One VPS, two independent services.

## Redeploying after a code change

```bash
sudo git -C /opt/xzx-bot pull --ff-only
sudo /opt/xzx-bot/.venv/bin/pip install -r /opt/xzx-bot/requirements.txt   # if deps changed
sudo systemctl restart xzx-bot
```

Railway auto-deployed on push; here you pull + restart. (You can automate it with
a GitHub Actions SSH deploy later if you want the old behaviour back.)

## Troubleshooting

- `systemctl status xzx-bot` and `journalctl -u xzx-bot -n 100` - most answers
  are in the log.
- Bot won't start: usually a missing `DISCORD_TOKEN` or a bad path in `.env`.
- Webhook/download links broken: `PUBLIC_URL` must start with `https://` and
  match the domain certbot secured.
- Permission denied on the DB/files: `sudo chown -R xzxbot:xzxbot /opt/xzx-bot/data`.
- Port already in use: the gang bot is on the same `PORT`; change one.
