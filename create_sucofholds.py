import os
from pathlib import Path

ROOT = Path("azure-rag-app")

FILES = {

    # ---------------- pyproject ----------------
    "pyproject.toml": '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "azure-rag-app"
version = "0.1.0"
description = "RAG app using Azure OpenAI, Azure AI Search, FastAPI, vanilla JS"
requires-python = ">=3.10"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "python-dotenv",
    "openai>=1.0.0",
    "azure-search-documents>=11.6.0",
    "azure-core>=1.30.0",
    "jinja2",
    "pydantic>=2.0.0"
]

[tool.hatch.build.targets.wheel]
packages = ["app"]
''',

    # ---------------- .env ----------------
    ".env": '''# Local development settings

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-aoai-key>
AZURE_OPENAI_API_VERSION=2024-05-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_API_KEY=<your-search-key>
AZURE_SEARCH_INDEX_NAME=docs-index
''',

    # ---------------- app core ----------------
    "app/__init__.py": "",
    "app/app.py": '''import os
from typing import List, Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models.chat import ChatRequest, ChatResponse
from app.services.openai_client import get_embedding, chat_with_context
from app.services.search_client import hybrid_retrieve

app = FastAPI(title="Azure RAG Web App")

BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def build_rag_messages(question: str, docs: List[Dict]) -> List[Dict]:
    context_chunks = []
    for i, d in enumerate(docs, start=1):
        source = d.get("source") or f"doc-{i}"
        content = d.get("content") or ""
        context_chunks.append(f"[{i}] Source: {source}\\n{content}")

    context_str = "\\n\\n".join(context_chunks) if context_chunks else "NO CONTEXT FOUND."

    system_prompt = (
        "You are a helpful assistant that answers questions using the context below.\\n"
        "If the answer cannot be found, say you don't know.\\n\\n"
        f"Context:\\n{context_str}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    question = req.messages[-1].content

    embedding = get_embedding(question)
    docs = hybrid_retrieve(question, embedding, top_k=req.top_k)
    messages = build_rag_messages(question, docs)
    answer = chat_with_context(messages)

    return ChatResponse(answer=answer, sources=docs)
''',

    # ---------------- config ----------------
    "app/config/__init__.py": "",
    "app/config/settings.py": '''import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large")

    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "docs-index")

settings = Settings()
''',

    # ---------------- models ----------------
    "app/models/__init__.py": "",
    "app/models/chat.py": '''from typing import List, Dict
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    top_k: int = 5

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict]
''',

    # ---------------- services ----------------
    "app/services/__init__.py": "",
    "app/services/openai_client.py": '''from typing import List
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
''',

    "app/services/search_client.py": '''from typing import List, Dict
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

from app.config.settings import settings

search_client = SearchClient(
    endpoint=settings.AZURE_SEARCH_ENDPOINT,
    index_name=settings.AZURE_SEARCH_INDEX_NAME,
    credential=AzureKeyCredential(settings.AZURE_SEARCH_API_KEY),
)

def hybrid_retrieve(query: str, embedding: List[float], top_k: int = 5):
    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=top_k,
        fields="contentVector"
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="default",
        select=["id", "content", "source"],
        top=top_k,
    )

    output = []
    for r in results:
        output.append({
            "id": r.get("id"),
            "content": r.get("content"),
            "source": r.get("source"),
        })
    return output
''',

    # ---------------- templates ----------------
    "app/templates/index.html": '''<!DOCTYPE html>
<html>
  <head>
    <title>Azure RAG Chat</title>
    <link rel="stylesheet" href="{{ url_for('static', path='/css/site.css') }}">
  </head>
  <body>
    <div class="app-container">
      <h1>Azure RAG Chat</h1>

      <div id="chat-window" class="chat-window"></div>

      <form id="chat-form" class="chat-form">
        <textarea id="user-input" class="chat-input" placeholder="Ask a question…" rows="3"></textarea>
        <button type="submit" class="chat-submit">Send</button>
      </form>

      <div id="status" class="status"></div>
    </div>

    <script src="{{ url_for('static', path='/js/chat.js') }}"></script>
  </body>
</html>
''',

    # ---------------- static files ----------------
    "app/static/css/site.css": "/* same CSS from before */",
    "app/static/js/chat.js": "/* same JS from before */",
}


def main():
    print(f"Creating project in: {ROOT.resolve()}")
    ROOT.mkdir(exist_ok=True)

    for rel_path, content in FILES.items():
        file_path = ROOT / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        print(f"Created: {rel_path}")

    print("\n✔ Scaffold created successfully!")
    print("\nNext steps:")
    print(f"  cd {ROOT.name}")
    print("  pip install -e .")
    print("  uvicorn app.app:app --reload")
    print("\nOpen http://localhost:8000/ in your browser.")


if __name__ == "__main__":
    main()
