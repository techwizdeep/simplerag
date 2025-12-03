from typing import List
from openai import AzureOpenAI
from app.config.settings import settings

client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
)

def get_embedding(text: str) -> List[float]:
    resp = client.embeddings.create(
        model=settings.AZURE_OPENAI_EMBED_DEPLOYMENT,
        input=text,
    )
    return resp.data[0].embedding

def chat_with_context(messages: list) -> str:
    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        temperature=0.1,
    )
    return resp.choices[0].message.content
