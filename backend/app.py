# backend/app/app.py
from pathlib import Path
from typing import List, Dict

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.models.chat import ChatRequest, ChatResponse
from app.services.openai_client import get_embedding, chat_with_context
from app.services.search_client import hybrid_retrieve
from app.auth.easyauth import get_current_user

app = FastAPI(title="Azure RAG Web App")

# ---------- Paths ----------
APP_DIR = Path(__file__).resolve().parent      # .../backend/app
BACKEND_DIR = APP_DIR.parent                   # .../backend
ROOT_DIR = BACKEND_DIR.parent                  # .../azure-rag-app
FRONTEND_DIR = ROOT_DIR / "frontend"           # .../frontend

TEMPLATE_DIR = FRONTEND_DIR / "template"       # .../frontend/template
STATIC_DIR = FRONTEND_DIR / "static"           # .../frontend/static

# Serve /static -> frontend/static
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# ---------- Helper: build RAG messages ----------
def build_rag_messages(question: str, docs: List[Dict]) -> List[Dict]:
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
    Serve the frontend HTML from frontend/template/index.html.
    """
    index_file = TEMPLATE_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("index.html not found", status_code=500)
    return FileResponse(index_file)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    RAG chat endpoint (protected by Easy Auth in Azure).
    """
    question = req.messages[-1].content

    # 1. Embed query
    embedding = get_embedding(question)

    # 2. Retrieve docs from Azure AI Search
    docs = hybrid_retrieve(question, embedding, top_k=req.top_k)

    # 3. Build messages with context
    messages = build_rag_messages(question, docs)

    # 4. Call Azure OpenAI
    answer = chat_with_context(messages)

    return ChatResponse(answer=answer, sources=docs)
