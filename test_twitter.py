import asyncio
import os
from dotenv import load_dotenv
from twitter_client import init_twitter_client, post_tweet

load_dotenv()


def test_twitter():
    print('Testing Twitter/X integration...')
    print()

    # Check credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

    if api_key:
        print(f'  API Key: {api_key[:5]}...{api_key[-4:]}')
    else:
        print('  API Key: MISSING')

    if api_secret:
        print(f'  API Secret: {api_secret[:5]}...{api_secret[-4:]}')
    else:
        print('  API Secret: MISSING')

    if access_token:
        print(f'  Access Token: {access_token[:5]}...{access_token[-4:]}')
    else:
        print('  Access Token: MISSING')

    if access_token_secret:
        print(f'  Access Token Secret: {access_token_secret[:5]}...{access_token_secret[-4:]}')
    else:
        print('  Access Token Secret: MISSING')

    print()

    # Initialize client
    client = init_twitter_client()
    if client is None:
        print('Failed to initialize Twitter client.')
        print()
        print('Possible solutions:')
        print('1. Add your Twitter API credentials to .env')
        print('2. Make sure TWITTER_ENABLED is set to true')
        print('3. Get credentials from https://developer.x.com/en/portal/dashboard')
        return

    print('Twitter client initialized!')
    print()

    # Post test tweet
    print('Attempting to post test tweet...')
    success = post_tweet(
        client,
        'Test tweet from PredictAll Bot!',
        'https://polymarket.com'
    )

    if success:
        print('Success! Test tweet posted. Check your Twitter/X profile.')
    else:
        print('Failed to post tweet. Check the error logs above.')
        print()
        print('Possible solutions:')
        print('1. Ensure your app has Read+Write permissions')
        print('2. Regenerate your Access Token after changing permissions')
        print('3. Check if your developer account is in good standing')


if __name__ == "__main__":
    test_twitter()
