#!/bin/bash
# Wrapper script to run the bot using the virtual environment

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Please copy .env.example to .env and configure your keys."
    echo "   cp .env.example .env"
    echo ""
fi

# Run the bot
echo "🚀 Starting Telegram Bot..."
./.venv/bin/python main.py
