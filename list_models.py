import os
import asyncio
from dotenv import load_dotenv
import openai

load_dotenv()

api_key = os.getenv("XAI_API_KEY")
if not api_key:
    print("No API Key found in .env")
    exit(1)

client = openai.AsyncOpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1",
)

async def list_models():
    try:
        models = await client.models.list()
        print("Available Models:")
        for model in models.data:
            print(f"- {model.id}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
