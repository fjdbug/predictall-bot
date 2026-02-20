import asyncio
import os
import datetime
from dotenv import load_dotenv
import openai

load_dotenv()

client = openai.AsyncOpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

async def check_freshness():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"Testing model with Current Date: {current_date}")
    
    try:
        completion = await client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Today is {current_date}. 1. What date do you think it is? 2. What is the latest news about 'SpaceX' from the last 24 hours? 3. Can you browse the web?"}
            ]
        )
        print("\nResponse:")
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_freshness())
