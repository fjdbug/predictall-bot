import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

async def get_updates():
    try:
        bot = Bot(TOKEN)
        me = await bot.get_me()
        print(f"🤖 Bot found: @{me.username} (ID: {me.id})")
        print("Checking for recent messages/updates...")
        
        updates = await bot.get_updates()
        
        if not updates:
            print("No updates found.")
            print("Action required: Please send a message to your bot or add it to the channel/group and send a message there.")
            return

        print("\n👇 Found the following Chat IDs:\n")
        for u in updates:
            chat = None
            if u.message:
                chat = u.message.chat
            elif u.channel_post:
                chat = u.channel_post.chat
            elif u.my_chat_member:
                chat = u.my_chat_member.chat
            
            if chat:
                print(f"   Name: {chat.title or chat.username or chat.first_name}")
                print(f"   Type: {chat.type}")
                print(f"   ID:   {chat.id}")
                print("   --------------------")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_updates())
