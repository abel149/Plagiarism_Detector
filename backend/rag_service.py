import os
import hashlib
import random
from typing import List
from openai import OpenAI
from sqlalchemy.orm import Session

from .models import AcademicSource


def _mock_embedding(text: str, dims: int = 1536) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8", "ignore")).digest()
    seed = int.from_bytes(digest[:8], "big", signed=False)
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dims)]

def get_embedding(text: str) -> List[float]:
    provider = (os.getenv("EMBEDDING_PROVIDER") or "openai").strip().lower()
    allow_mock = (os.getenv("ALLOW_MOCK_EMBEDDINGS") or "").strip().lower() in {"1", "true", "yes"}

    if provider == "mock":
        return _mock_embedding(text)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        if allow_mock:
            return _mock_embedding(text)
        raise RuntimeError('OPENAI_API_KEY not set')

    try:
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(input=text, model='text-embedding-3-small')
        return resp.data[0].embedding
    except Exception:
        if allow_mock:
            return _mock_embedding(text)
        raise

def query_sources(db: Session, query_text: str, top_k: int = 5):
    emb = get_embedding(query_text)
    rows = (
        db.query(
            AcademicSource.id,
            AcademicSource.title,
            AcademicSource.authors,
            AcademicSource.publication_year,
            AcademicSource.abstract,
            AcademicSource.source_type,
            AcademicSource.embedding.l2_distance(emb).label("distance"),
        )
        .filter(AcademicSource.embedding.isnot(None))
        .order_by("distance")
        .limit(top_k)
        .all()
    )

    return [
        {
            "id": r.id,
            "title": r.title,
            "authors": r.authors,
            "year": r.publication_year,
            "abstract": r.abstract,
            "source_type": r.source_type,
            "distance": float(r.distance) if r.distance is not None else None,
        }
        for r in rows
    ]
