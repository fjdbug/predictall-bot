import asyncio
import json
import sqlite3
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

import openai
from dotenv import load_dotenv
from telegram import Bot, constants
from telegram.error import TelegramError

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WATCH_TOPIC = os.getenv("WATCH_TOPIC", "Artificial Intelligence News")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 600))

# Initialize OpenAI Client for xAI
if not XAI_API_KEY:
    logger.error("XAI_API_KEY is missing via .env")
    exit(1)

if XAI_API_KEY.startswith("your_") or "xai_api_key_here" in XAI_API_KEY:
    logger.error("❌ Invalid API Key detected! Please update .env with your actual xAI API key.")
    logger.error("   Open the .env file and replace 'your_xai_api_key_here' with your real key.")
    exit(1)

client = openai.AsyncOpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

# Database Setup
DB_FILE = "bot_memory.db"

def init_db():
    """Initialize the SQLite database for deduplication."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_items (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_seen(item_id: str) -> bool:
    """Check if an item ID has already been processed."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM seen_items WHERE id = ?', (item_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_seen(item_id: str):
    """Mark an item ID as processed."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO seen_items (id) VALUES (?)', (item_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    finally:
        conn.close()

def cleanup_old_records(days: int = 30):
    """Delete database records older than the specified number of days."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM seen_items WHERE timestamp < datetime("now", ?)',
        (f'-{days} days',)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        logger.info(f"🗑️ Archived {deleted} records older than {days} days.")

# Telegram Bot Setup
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing via .env")
    exit(1)

telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

from bs4 import BeautifulSoup
from googlenewsdecoder import new_decoderv1

def resolve_google_news_url(url: str) -> str:
    """Resolve a Google News RSS redirect URL to the real article URL."""
    if not url or 'news.google.com' not in url:
        return url
    try:
        decoded = new_decoderv1(url)
        if decoded.get('status'):
            real_url = decoded['decoded_url']
            logger.info(f"Resolved Google News URL -> {real_url[:80]}...")
            return real_url
    except Exception as e:
        logger.warning(f"Failed to decode Google News URL: {e}")
    return url  # Return original if decoding fails

# Blocklist for generic/logo images that shouldn't be sent
BLOCKED_IMAGE_DOMAINS = [
    "lh3.googleusercontent.com",  # Google News logo
    "news.google.com",
]

def is_valid_article_image(image_url: str) -> bool:
    """Check if the image URL is a real article image, not a generic logo."""
    if not image_url:
        return False
    for domain in BLOCKED_IMAGE_DOMAINS:
        if domain in image_url:
            logger.info(f"Blocked generic image: {image_url[:80]}...")
            return False
    return True

async def extract_og_image(url: str) -> str:
    """Extract Open Graph image (og:image) from a news article URL."""
    if not url:
        return ""
    
    # First: resolve Google News redirect to get the REAL article URL
    real_url = resolve_google_news_url(url)
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http_client:
            response = await http_client.get(real_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try og:image first (most common)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                img = og_image["content"]
                if is_valid_article_image(img):
                    return img
            
            # Try twitter:image as fallback
            tw_image = soup.find("meta", attrs={"name": "twitter:image"})
            if tw_image and tw_image.get("content"):
                img = tw_image["content"]
                if is_valid_article_image(img):
                    return img
            
            return ""
    except Exception as e:
        logger.warning(f"Failed to extract og:image from {real_url}: {e}")
        return ""

async def send_notification(item: Dict[str, str]) -> bool:
    """Send a formatted message to Telegram with image if available."""
    headline = item.get("headline", "No Headline")
    url = item.get("url", "")
    image_url = item.get("image_url", "")
    
    caption = f"<b>JUST IN:</b> {headline}\n\n"
    if url:
        caption += f"<a href='{url}'>Source</a>"

    try:
        if image_url:
            # Send as photo with caption (like the reference screenshot)
            await telegram_bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=image_url,
                caption=caption,
                parse_mode=constants.ParseMode.HTML
            )
        else:
            # Fallback to text-only message
            await telegram_bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=caption,
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=False
            )
        logger.info(f"Sent notification: {headline}")
        return True
    except TelegramError as e:
        logger.error(f"Failed to send Telegram message: {e}")
        # If photo send fails (e.g., invalid image URL), try text-only
        if image_url:
            try:
                await telegram_bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=caption,
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=False
                )
                logger.info(f"Sent text-only fallback: {headline}")
                return True
            except TelegramError as e2:
                logger.error(f"Fallback also failed: {e2}")
        return False
        
import hashlib
import feedparser
import httpx

async def validate_url(url: str) -> bool:
    """Check if the URL is accessible (HTTP 200-399)."""
    if not url or not url.startswith("http"):
        return False
        
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Try HEAD first
            response = await client.head(url)
            if response.status_code == 405: # Method Not Allowed
                response = await client.get(url, headers={"Range": "bytes=0-100"}) # Try partial GET
            
            return 200 <= response.status_code < 400
    except Exception as e:
        logger.warning(f"Link validation failed for {url}: {e}")
        return False

async def fetch_updates(topic: str) -> List[Dict[str, str]]:
    """Fetch latest updates from Google News RSS and filter/summarize with xAI."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Google News RSS URL for "prediction market" in Philippines locale
    # q=prediction+market matches user request
    rss_url = "https://news.google.com/rss/search?q=prediction+market&hl=en-PH&gl=PH&ceid=PH:en"
    
    try:
        logger.info(f"Fetching RSS feed: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            logger.info("No entries found in RSS feed.")
            return []

        # 2. Format entries for Grok
        # We perform initial filtering here to keep context small
        rss_context = "News Items:\n\n"
        # Take top 15 items
        for i, entry in enumerate(feed.entries[:15], 1):
            title = entry.get('title', 'No Title')
            link = entry.get('link', '')
            pubDate = entry.get('published', '')
            rss_context += f"{i}. Title: {title}\n   Link: {link}\n   Date: {pubDate}\n\n"

        # 3. Ask Grok to process these items
        completion = await client.chat.completions.create(
            model="grok-4-fast-reasoning",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a news aggregator. Today is {current_date}. "
                        "I will provide you with a list of RSS News Items. "
                        "Your job is to select the most relevant and recent news items from this list. "
                        "Return a JSON object with a single key 'news' which is a list of objects. "
                        "Each object must have: "
                        "- 'headline': A concise headline based on the RSS item. "
                        "- 'url': The EXACT Link provided in the RSS item. "
                        "Do not include any text outside the JSON object. "
                        "If no results are relevant, return an empty list."
                    )
                },
                {"role": "user", "content": f"Here are the news items:\n\n{rss_context}"}
            ],
            temperature=0.2, # Low temperature for factual extraction
        )

        response_content = completion.choices[0].message.content.strip()
        # Handle potential markdown code blocks
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        
        data = json.loads(response_content.strip())
        news_items = data.get("news", [])
        
        # 4. Generate Deterministic IDs & VALIDATE LINKS
        processed_items = []
        for item in news_items:
            url = item.get("url", "")
            headline = item.get("headline", "")
            
            # Resolve Google News redirect URL to the REAL article URL
            if url and 'news.google.com' in url:
                real_url = resolve_google_news_url(url)
                item["url"] = real_url  # Replace with real URL everywhere
                url = real_url
            
            # Validate URL before processing
            if url:
                 if not await validate_url(url):
                     logger.warning(f"Skipping broken link: {url}")
                     continue
            
            # Extract article image from the REAL article page
            if url:
                image_url = await extract_og_image(url)
                if image_url:
                    item["image_url"] = image_url
                    logger.info(f"Found image for: {headline[:50]}...")
            
            # Create a deterministic ID based on the URL (preferred) or headline
            if url:
                item_id = hashlib.md5(url.encode()).hexdigest()
            else:
                item_id = hashlib.md5(headline.encode()).hexdigest()
                
            item["id"] = item_id
            processed_items.append(item)
            
        return processed_items

    except Exception as e:
        logger.error(f"Error fetching updates: {e}")
        return []

async def main():
    """Main async loop."""
    logger.info("🤖 Bot started. Initializing database...")
    init_db()
    logger.info(f"👀 Monitoring topic: {WATCH_TOPIC}")
    logger.info(f"⏱️ Poll interval: {POLL_INTERVAL} seconds")

    while True:
        try:
            # Auto-archive old records to keep DB small
            cleanup_old_records(30)
            
            logger.info("Fetching updates...")
            updates = await fetch_updates(WATCH_TOPIC)
            
            new_count = 0
            for item in updates:
                item_id = item.get("id")
                if not item_id:
                    continue
                
                if not is_seen(item_id):
                    logger.info(f"New item found: {item_id}")
                    if await send_notification(item):
                        mark_seen(item_id)
                        new_count += 1
            
            if new_count == 0:
                logger.info("No new updates found.")
                
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
