import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

async def test_message():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print(f"Testing with Token: {token[:5]}...{token[-5:]}")
    print(f"Testing with Chat ID: {chat_id}")
    
    if not token or not chat_id:
        print("Error: Missing credentials in .env")
        return

    bot = Bot(token=token)
    
    try:
        print("Attempting to send message...")
        await bot.send_message(chat_id=chat_id, text="🚀 Test message from Scraper Bot!")
        print("✅ Success! Message sent.")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        print("\nPossible solutions:")
        print("1. Ensure the bot is added to the channel.")
        print("2. Ensure the bot is an ADMINISTRATOR of the channel.")
        print("3. Verify the Chat ID (try -100 prefix if not present).")

if __name__ == "__main__":
    asyncio.run(test_message())
