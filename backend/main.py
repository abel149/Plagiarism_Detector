import os
import shutil

import requests
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from . import models, auth
from .models import Base, Student, Assignment, AnalysisResult
from .rag_service import query_sources

load_dotenv()

DB_HOST = os.getenv('POSTGRES_HOST', 'postgres')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'academic_helper')
DB_USER = os.getenv('POSTGRES_USER', 'student')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'secure_password')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="Academic Assignment Helper")


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    student_id: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str

@app.on_event('startup')
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.post('/auth/register')
def register(payload: RegisterRequest):
    db = SessionLocal()
    try:
        if db.query(Student).filter(Student.email == payload.email).first():
            raise HTTPException(status_code=400, detail='Email already registered')
        hashed = auth.get_password_hash(payload.password)
        user = Student(
            email=payload.email,
            password_hash=hashed,
            full_name=payload.full_name,
            student_id=payload.student_id,
        )
        db.add(user)
        db.commit()
        return {"message": "registered"}
    finally:
        db.close()

@app.post('/auth/login')
def login(payload: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(Student).filter(Student.email == payload.email).first()
        if not user or not auth.verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail='Invalid credentials')
        token = auth.create_access_token(user.email, role="student")
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()

@app.post('/upload')
def upload(file: UploadFile = File(...), token_payload: dict = Depends(auth.require_student)):
    db = SessionLocal()
    try:
        user_email = token_payload.get('sub')
        user = db.query(Student).filter(Student.email == user_email).first()
        if not user:
            raise HTTPException(status_code=401, detail='User not found')

        uploads_dir = os.getenv("UPLOAD_DIR", "/uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        safe_name = os.path.basename(file.filename)
        dest_path = os.path.join(uploads_dir, safe_name)
        with open(dest_path, 'wb') as out:
            shutil.copyfileobj(file.file, out)

        assignment = Assignment(student_id=user.id, filename=safe_name)
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        n8n_url = os.getenv('N8N_WEBHOOK_URL') or os.getenv('N8N_WEBHOOK', 'http://n8n:5678/webhook/assignment')
        try:
            resp = requests.post(
                n8n_url,
                json={
                    "assignment_id": assignment.id,
                    "file_path": dest_path,
                    "student_email": user.email,
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"n8n webhook error: {resp.status_code}")
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach n8n webhook: {str(e)}")

        return {"job_id": assignment.id}
    finally:
        db.close()

@app.get('/analysis/{assignment_id}')
def get_analysis(assignment_id: int, token_payload: dict = Depends(auth.require_student)):
    db = SessionLocal()
    try:
        user_email = token_payload.get('sub')
        user = db.query(Student).filter(Student.email == user_email).first()
        if not user:
            raise HTTPException(status_code=401, detail='User not found')
        analysis = db.query(AnalysisResult).filter(AnalysisResult.assignment_id == assignment_id).first()
        if not analysis:
            raise HTTPException(status_code=404, detail='Analysis not ready')
        return JSONResponse(content={
            "assignment_id": assignment_id,
            "suggested_sources": analysis.suggested_sources,
            "plagiarism_score": analysis.plagiarism_score,
            "flagged_sections": analysis.flagged_sections,
            "research_suggestions": analysis.research_suggestions,
            "citation_recommendations": analysis.citation_recommendations,
            "confidence_score": analysis.confidence_score
        })
    finally:
        db.close()

@app.get('/sources')
def search_sources(q: str, token_payload: dict = Depends(auth.require_student)):
    db = SessionLocal()
    try:
        results = query_sources(db, q)
        return {"results": results}
    finally:
        db.close()
