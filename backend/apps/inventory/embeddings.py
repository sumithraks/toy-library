import logging

import voyageai
from django.conf import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "voyage-4-lite"


def embed_text(text, input_type="document"):
    """Embed a single string via Voyage AI. `input_type` should be "document" when
    embedding text to store, or "query" when embedding a free-form search string --
    Voyage optimizes the vector differently for each side of a retrieval task."""
    if not settings.VOYAGE_API_KEY:
        raise ValueError("Semantic search is not configured (missing VOYAGE_API_KEY)")

    client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    result = client.embed([text], model=EMBEDDING_MODEL, input_type=input_type)
    return result.embeddings[0]
