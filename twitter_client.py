"""
Twitter/X Client Module for PredictAll Bot.

Handles authentication and posting tweets via the Twitter API v2 (using tweepy).
Supports image uploads using the same og:image used for Telegram.
"""

import os
import logging
import tempfile
from typing import Optional, Tuple

import tweepy
import httpx

logger = logging.getLogger(__name__)

TWEET_MAX_LENGTH = 280


def init_twitter_client() -> Optional[Tuple[tweepy.Client, tweepy.API]]:
    """
    Initialize and return a tweepy Client + API pair.
    Client is used for v2 tweet creation, API is used for v1.1 media uploads.
    Returns None if credentials are missing or TWITTER_ENABLED is false.
    """
    enabled = os.getenv("TWITTER_ENABLED", "true").lower()
    if enabled not in ("true", "1", "yes"):
        logger.info("Twitter posting is DISABLED (TWITTER_ENABLED=%s).", enabled)
        return None

    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    missing = []
    if not api_key:
        missing.append("TWITTER_API_KEY")
    if not api_secret:
        missing.append("TWITTER_API_SECRET")
    if not access_token:
        missing.append("TWITTER_ACCESS_TOKEN")
    if not access_token_secret:
        missing.append("TWITTER_ACCESS_TOKEN_SECRET")

    if missing:
        logger.warning(
            "Twitter credentials missing (%s). Tweeting disabled.",
            ", ".join(missing),
        )
        return None

    try:
        # v2 Client for creating tweets
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        # v1.1 API for media uploads (not available in v2)
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)

        logger.info("Twitter client initialized successfully.")
        return (client, api)
    except Exception as e:
        logger.error("Failed to initialize Twitter client: %s", e)
        return None


def compose_tweet(headline: str) -> str:
    """
    Compose a tweet from a headline (no links).
    Ensures the total length does not exceed 280 characters.
    """
    prefix = "JUST IN: "
    max_headline_len = TWEET_MAX_LENGTH - len(prefix) - 3  # -3 for "..."

    if len(prefix) + len(headline) > TWEET_MAX_LENGTH:
        headline = headline[:max_headline_len].rstrip() + "..."

    return prefix + headline


def _download_image(image_url: str) -> Optional[str]:
    """Download an image to a temp file and return the file path."""
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as http:
            response = http.get(image_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            if response.status_code != 200:
                logger.warning("Failed to download image (HTTP %s): %s", response.status_code, image_url[:80])
                return None

            # Determine file extension from content type
            content_type = response.headers.get("content-type", "")
            if "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                ext = ".jpg"

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.write(response.content)
            tmp.close()
            return tmp.name
    except Exception as e:
        logger.warning("Failed to download image: %s", e)
        return None


def post_tweet(twitter_client, headline: str, image_url: str = "") -> bool:
    """
    Post a tweet with the given headline and optional image.

    Args:
        twitter_client: Tuple of (tweepy.Client, tweepy.API) from init_twitter_client(), or None.
        headline: The news headline to tweet.
        image_url: Optional URL of the article image (same one used for Telegram).

    Returns True if the tweet was posted successfully, False otherwise.
    Never raises -- a failed tweet should not crash the bot.
    """
    if twitter_client is None:
        return False

    client, api = twitter_client
    tweet_text = compose_tweet(headline)
    media_ids = None

    # Upload image if available
    if image_url:
        tmp_path = _download_image(image_url)
        if tmp_path:
            try:
                media = api.media_upload(filename=tmp_path)
                media_ids = [media.media_id]
                logger.info("Image uploaded to Twitter (media_id: %s)", media.media_id)
            except Exception as e:
                logger.warning("Failed to upload image to Twitter: %s", e)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    try:
        response = client.create_tweet(text=tweet_text, media_ids=media_ids)
        tweet_id = response.data.get("id", "unknown")
        has_image = " + image" if media_ids else ""
        logger.info("Tweet posted (ID: %s%s): %s", tweet_id, has_image, headline[:60])
        return True
    except tweepy.TooManyRequests:
        logger.warning("Twitter rate limit reached. Skipping tweet: %s", headline[:60])
        return False
    except tweepy.Forbidden as e:
        logger.error("Twitter API forbidden (check app permissions): %s", e)
        return False
    except tweepy.Unauthorized as e:
        logger.error("Twitter auth failed (check credentials): %s", e)
        return False
    except Exception as e:
        logger.error("Failed to post tweet: %s", e)
        return False
