from typing import List, Dict
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
