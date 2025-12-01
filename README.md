# Telegram LLM Bot

A simple Telegram bot that asks for user input and returns the entered text when the "Ask LLM" button is pressed.

## Features

- Asks user for input (question)
- Displays "Ask LLM" button
- Returns the entered text when button is pressed

## Setup

1. Create a Telegram bot using BotFather (https://t.me/BotFather) and obtain your bot token
2. Add your bot token to `.secret/bot-token.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Usage

1. Start a conversation with your bot
2. Send any text message (question)
3. Press the "Ask LLM" button that appears
4. The bot will return your original message

## How It Works

The bot uses the python-telegram-bot library to:
1. Listen for incoming messages
2. Store the user's question in the session
3. Display an inline button "Ask LLM"
4. When pressed, return the stored question

## Security

- Bot token is stored in `.secret/bot-token.env` which should NOT be committed to version control
- The `.secret` directory is excluded from version control
