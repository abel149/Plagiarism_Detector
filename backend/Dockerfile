FROM python:3.11-slim
WORKDIR /app

# Copy requirements from backend folder and install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package into the image
COPY backend /app/backend
COPY data /app/data
RUN mkdir -p /app/backend/uploads

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
