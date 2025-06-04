# Simple Telegram Redirect Bot

This repository contains a minimal Telegram bot written in Python. It forwards any incoming message from a user directly to a specified admin chat.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export the bot token and admin chat ID as environment variables:
   ```bash
   export BOT_TOKEN="<your-bot-token>"
   export ADMIN_CHAT_ID=<admin-user-id>
   ```
3. Run the bot:
   ```bash
   python bot.py
   ```

The bot will start polling and forward every received message to the admin.
