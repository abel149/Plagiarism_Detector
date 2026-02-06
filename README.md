# Academic Assignment Helper & Plagiarism Detector (RAG-Powered)

This project provides a Dockerized backend + n8n automation system that lets students register, log in, upload assignments, and receive AI-assisted analysis backed by a vector database.

**What this system does**

1. Students register and log in via a FastAPI API using JWT authentication.
2. Students upload assignment files through a secured endpoint.
3. The backend triggers an n8n workflow to extract text, run RAG-based source lookup, and compute plagiarism-like similarity.
4. Results are stored in PostgreSQL and can be retrieved by the student.

**Services**

- `backend`: FastAPI API with JWT auth, file upload, and RAG search endpoints.
- `n8n`: Workflow automation for extraction, AI analysis, and result storage.
- `postgres`: PostgreSQL with `pgvector` for embeddings.

**Project structure**

- `backend/` FastAPI source code.
- `data/` Sample academic sources for ingestion.
- `init_db/` Postgres init scripts for extensions.
- `postgres/` Docker image build context for Postgres + pgvector.
- `uploads/` Uploaded assignment files (bind-mounted into containers).
- `workflows/` n8n workflow export placeholder.

## Quick start (Windows PowerShell)

1. Copy `.env.example` to `.env` and fill in values.
2. Build and start services:

```powershell
docker compose up --build
```

3. Backend will be available at `http://localhost:8000`.
4. n8n will be available at `http://localhost:5678`.

## Environment variables

These are the expected values in `.env`:

- `OPENAI_API_KEY` API key for embeddings and AI analysis.
- `POSTGRES_DB` Database name.
- `POSTGRES_USER` Database user.
- `POSTGRES_PASSWORD` Database password.
- `POSTGRES_HOST` Typically `postgres` inside Docker.
- `POSTGRES_PORT` Typically `5432`.
- `JWT_SECRET_KEY` Secret used to sign JWTs.
- `N8N_WEBHOOK_URL` Webhook URL for the n8n workflow.
- `EMBEDDING_PROVIDER` `openai` or `mock`.
- `ALLOW_MOCK_EMBEDDINGS` `true` to allow mock embeddings if API key is missing.

## API endpoints

All endpoints are served by the FastAPI backend:

- `POST /auth/register` Register a student account.
- `POST /auth/login` Log in and receive a JWT token.
- `POST /upload` Upload an assignment file and trigger n8n. Requires JWT.
- `GET /analysis/{id}` Retrieve analysis results. Requires JWT.
- `GET /sources?q=...` Search academic sources via vector similarity. Requires JWT.

## RAG and embeddings

Embeddings are stored in PostgreSQL using `pgvector`. The `backend/rag_service.py` module:

- Generates embeddings using OpenAI (`text-embedding-3-small`).
- Falls back to a deterministic mock embedding generator if enabled.
- Performs similarity search using `l2_distance` on stored vectors.

## Ingest sample academic sources

Before testing RAG search, load sample data:

```powershell
python -m backend.ingest_sample
```

This reads `data/sample_academic_sources.json`, generates embeddings, and inserts rows into `academic_sources`.

## n8n workflow

The backend calls the n8n webhook configured by `N8N_WEBHOOK_URL`. The intended workflow steps:

1. Receive file path and metadata.
2. Extract text (PDF or DOCX).
3. Query the vector database for related sources.
4. Call an AI model to summarize topic and key themes.
5. Compute plagiarism-like similarity signals.
6. Store structured results in `analysis_results`.

Export the workflow from the n8n UI to:

- `workflows/assignment_analysis_workflow.json`

## Demo walkthrough (5 minutes)

1. Start services:

```powershell
docker compose up --build
```

2. Register a student:

```powershell
curl -X POST http://localhost:8000/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"student@test.com\",\"password\":\"pass123\",\"full_name\":\"Test Student\",\"student_id\":\"S123\"}"
```

3. Log in to get a JWT:

```powershell
curl -X POST http://localhost:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"student@test.com\",\"password\":\"pass123\"}"
```

4. Upload an assignment (replace `YOUR_TOKEN` and file path):

```powershell
curl -X POST http://localhost:8000/upload ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -F "file=@sample.docx"
```

5. Show n8n workflow execution at `http://localhost:5678`.
6. Fetch analysis results:

```powershell
curl -X GET http://localhost:8000/analysis/1 ^
  -H "Authorization: Bearer YOUR_TOKEN"
```

7. Search sources:

```powershell
curl -X GET "http://localhost:8000/sources?q=climate%20change" ^
  -H "Authorization: Bearer YOUR_TOKEN"
```

8. Verify database rows:

```powershell
docker exec -it plagiarism_detector-postgres-1 psql -U student -d academic_helper
```

Then in `psql`:

```sql
SELECT * FROM students;
SELECT * FROM assignments;
SELECT * FROM analysis_results;
```

## Notes

- Ensure `uploads/` exists so files can be stored and accessed by n8n.
- If you do not have an API key, set `ALLOW_MOCK_EMBEDDINGS=true` to test the flow.
- n8n workflow must be created in the UI and exported to `workflows/assignment_analysis_workflow.json`.
