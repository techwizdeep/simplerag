import os
from typing import List, Dict

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models.chat import ChatRequest, ChatResponse
from app.services.openai_client import get_embedding, chat_with_context
from app.services.search_client import hybrid_retrieve
from app.auth.easyauth import get_current_user

# FastAPI app
app = FastAPI(title="Azure RAG Web App with Easy Auth")

# Paths for templates and static files (relative to this file)
BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)


# ---------- Utility: build RAG prompt ----------

def build_rag_messages(question: str, docs: List[Dict]) -> List[Dict]:
    """
    Build the system + user messages for RAG using retrieved documents.
    """
    context_chunks = []
    for i, d in enumerate(docs, start=1):
        source = d.get("source") or f"doc-{i}"
        content = d.get("content") or ""
        context_chunks.append(f"[{i}] Source: {source}\n{content}")

    context_str = "\n\n".join(context_chunks) if context_chunks else "NO CONTEXT FOUND."

    system_prompt = (
        "You are a helpful assistant that answers questions using ONLY the context "
        "below. If the answer cannot be found in the context, say you don't know.\n\n"
        f"Context:\n{context_str}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Main page – serves the chat UI (templates/index.html).
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    RAG chat endpoint.

    - Easy Auth must have authenticated the user already (on Azure).
    - Locally, get_current_user can be configured to bypass auth for dev.
    """
    # current_user contains info from Easy Auth (e.g., email, user_id, name)
    # You can log or use it for per-user behavior if needed:
    #   print("Current user:", current_user)

    question = req.messages[-1].content

    # 1. Embed query
    embedding = get_embedding(question)

    # 2. Retrieve relevant docs from Azure AI Search
    docs = hybrid_retrieve(question, embedding, top_k=req.top_k)

    # 3. Build messages for Azure OpenAI with context
    messages = build_rag_messages(question, docs)

    # 4. Get model answer
    answer = chat_with_context(messages)

    # 5. Return answer + sources for UI to display
    return ChatResponse(answer=answer, sources=docs)
