# Telegram Bot Project

## Overview
This is a Telegram bot project originally designed for Render deployment, successfully migrated and configured for the Replit environment. The bot provides administrative commands and scheduled messaging functionality for "La Legione dei Risparmiatori" Telegram channel.

## Recent Changes
**September 25, 2025:**
- Migrated from Render webhook deployment to Replit polling mode
- Updated bot.py to use polling instead of webhooks for better compatibility with Replit
- Configured development workflow to run the bot with console output
- Set up deployment configuration for production (VM mode)
- Installed all Python dependencies from requirements.txt

## Project Architecture
```
├── bot.py              # Main bot application (entry point)
├── handlers.py         # Command handlers for /start, /test, /forza_invio
├── scheduler.py        # Scheduled message functionality
├── database.py         # SQLite database initialization and operations
├── requirements.txt    # Python dependencies
└── .replit            # Replit configuration
```

## Required Environment Variables
The bot requires these secrets to be set in Replit:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `ADMIN_IDS`: Comma-separated list of admin user IDs (e.g., "123456789,987654321")
- `CHANNEL_ID`: Target Telegram channel ID for messages

## Features
- `/start` - Welcome message for users
- `/test` - Send test message to channel (admin only)
- `/forza_invio` - Force send scheduled message (admin only)
- SQLite database for future data storage
- Admin permission system
- Error handling and logging

## Development Setup
1. Set the required environment variables in Replit Secrets
2. The bot automatically runs in polling mode suitable for development
3. Console logs show bot status and any errors
4. Database is automatically initialized on startup

## Deployment
Configured for VM deployment on Replit with persistent running suitable for a Telegram bot that needs to maintain connections and state.