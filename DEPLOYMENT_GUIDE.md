# XHOST Bot Deployment Guide

## What This Bot Does

**XHOST** is a Telegram bot for hosting and managing Python/JavaScript scripts. It allows users to:

- Upload `.py`, `.js`, or `.zip` files
- Run scripts as background processes
- Start/stop/restart scripts
- View script logs
- Send commands to running scripts
- Get notified about new users (owner only)

**Admin Features:**
- Manage subscriptions (file upload limits)
- Broadcast messages to all users
- Lock/unlock the bot
- Manage admin users
- View statistics

---

## Prerequisites

```bash
# Python 3.7+
python3 --version

# Install dependencies
pip install -r requirements.txt
```

**Create requirements.txt:**
```
pyTelegramBotAPI==4.14.0
python-dotenv==1.0.0
psutil==5.10.0
Flask==3.0.0
requests==2.31.0
```

---

## Local Setup

### 1. Clone/Setup the Bot

```bash
cd /home/null
```

### 2. Create `.env` File

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with YOUR credentials:
```bash
nano .env
```

**Fill in:**
- `TELEGRAM_BOT_TOKEN`: Get from @BotFather on Telegram
- `OWNER_ID`: Your Telegram user ID (use @userinfobot)
- `ADMIN_ID`: Usually same as OWNER_ID
- `BOT_USERNAME`: Your bot's name (e.g., `my_file_host_bot`)
- `UPDATE_CHANNEL`: Your Telegram channel for updates
- `PORT`: Flask port (8080 is fine for local)

### 3. Test Locally

```bash
python3 XHOST.py
```

Expected output:
```
✅ Bot initialized with token (last 10 chars: ...K8uw)
Flask Keep-Alive server started on port 8080
🚀 Starting polling...
```

### 4. Talk to Your Bot

Open Telegram and find your bot (use @BotFather to get the link), then click "START"

---

## Remote Deployment (Your Server)

### Option A: systemd Service (Recommended)

**1. Copy bot to server:**
```bash
scp -P 9922 -r /home/null/XHOST.py .env requirements.txt nulladmin@95.217.132.221:/home/nulladmin/xhost/
```

**2. SSH into server:**
```bash
ssh nulladmin@95.217.132.221 -p 9922
```

**3. Setup Python environment:**
```bash
cd /home/nulladmin/xhost
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Create systemd service** (`/etc/systemd/system/xhost-bot.service`):

```ini
[Unit]
Description=XHOST Telegram Bot
After=network.target

[Service]
Type=simple
User=nulladmin
WorkingDirectory=/home/nulladmin/xhost
Environment="PATH=/home/nulladmin/xhost/venv/bin"
ExecStart=/home/nulladmin/xhost/venv/bin/python3 XHOST.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**5. Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable xhost-bot
sudo systemctl start xhost-bot
sudo systemctl status xhost-bot
```

**View logs:**
```bash
sudo journalctl -u xhost-bot -f
```

---

### Option B: Screen (Simple)

```bash
ssh nulladmin@95.217.132.221 -p 9922
cd /home/nulladmin/xhost
source venv/bin/activate
screen -S xhost-bot
python3 XHOST.py
# Press Ctrl+A then D to detach
```

Reattach later:
```bash
screen -r xhost-bot
```

---

## First Time Setup

After bot is running:

1. **Send `/start` to bot** in Telegram
2. **Check bot logs** for "New user" notification
3. **Upload a test script**:
   - Create `test.py`:
     ```python
     print("✅ Bot is working!")
     import time
     while True:
         print("Running...")
         time.sleep(5)
     ```
   - Send to bot via "📤 Upload File"
4. **Monitor logs** in `inf/bot_data.log`

---

## File Structure

After first run:
```
/home/nulladmin/xhost/
├── XHOST.py                    # Main bot code
├── .env                        # Configuration (KEEP SECRET!)
├── requirements.txt            # Python packages
├── upload_bots/               # User script folders
│   ├── 6710320744/           # Your user folder
│   │   ├── test.py           # Your uploaded script
│   │   └── test.log          # Script output logs
│   └── other_user_id/
├── inf/                       # Data directory
│   ├── bot_data.db           # SQLite database
│   └── bot_data.log          # Bot logs
```

---

## Security Notes

⚠️ **NEVER commit `.env` to Git!**

Add to `.gitignore`:
```
.env
__pycache__/
*.pyc
inf/
upload_bots/
*.log
venv/
```

---

## Troubleshooting

**Bot doesn't start:**
```bash
# Check token is set
echo $TELEGRAM_BOT_TOKEN
grep TELEGRAM_BOT_TOKEN .env

# Check logs
python3 XHOST.py 2>&1 | head -20
```

**Port 8080 in use:**
```bash
# Change PORT in .env to 8081
# Or kill existing process: lsof -ti:8080 | xargs kill -9
```

**Scripts not running:**
- Check `inf/bot_data.log` for errors
- Ensure Python/Node.js installed on server
- Check file permissions in `upload_bots/`

**Database locked:**
- Stop bot: `systemctl stop xhost-bot`
- Delete/backup `inf/bot_data.db`
- Restart bot

---

## Admin Commands

Once running, in Telegram chat with bot:

- `/start` - Main menu
- `/status` - Bot statistics
- `/lockbot` - Lock bot (admin only)
- `/broadcast` - Send message to all users (admin only)
- `/adminpanel` - Manage admins (owner only)

---

## Important Variables from Code

From the audit, here's what the bot tracks:

| Variable | Purpose |
|----------|---------|
| `FREE_USER_LIMIT` (10) | Max files for free users |
| `SUBSCRIBED_USER_LIMIT` (15) | Max files for premium users |
| `ADMIN_LIMIT` (999) | Max files for admins |
| `OWNER_LIMIT` (∞) | Unlimited for owner |
| `max_file_size` (20MB) | Max upload size |

To change limits, edit lines 58-62 in XHOST.py.

---

## Next Steps

1. ✅ Create `.env` with your credentials
2. ✅ Install dependencies: `pip install -r requirements.txt`
3. ✅ Test locally: `python3 XHOST.py`
4. ✅ Deploy to server using Option A or B
5. ✅ Send `/start` to test
6. ✅ Upload test script to verify
7. ✅ Set up backup for `inf/bot_data.db`

Let me know if you need help with any step!
