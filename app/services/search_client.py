from typing import List, Dict
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
