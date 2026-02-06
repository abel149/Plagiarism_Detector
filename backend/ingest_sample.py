import json
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Base, AcademicSource
from backend.rag_service import get_embedding

DB_HOST = os.getenv('POSTGRES_HOST', 'postgres')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'academic_helper')
DB_USER = os.getenv('POSTGRES_USER', 'student')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'secure_password')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def ingest_sample(file_path='data/sample_academic_sources.json'):
    p = Path(file_path)
    if not p.exists():
        candidate = Path(__file__).resolve().parent.parent / 'data' / 'sample_academic_sources.json'
        if candidate.exists():
            p = candidate
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    db = SessionLocal()
    try:
        for item in data:
            text_for_embedding = (item.get('abstract') or '') + "\n\n" + (item.get('full_text') or '')
            text_for_embedding = text_for_embedding.strip() or (item.get('title') or '')
            emb = get_embedding(text_for_embedding)
            src = AcademicSource(
                title=item.get('title'),
                authors=','.join(item.get('authors', [])),
                publication_year=item.get('year'),
                abstract=item.get('abstract'),
                full_text=item.get('full_text'),
                source_type=item.get('type'),
                embedding=emb,
            )
            db.add(src)
        db.commit()
    finally:
        db.close()

if __name__ == '__main__':
    ingest_sample()
