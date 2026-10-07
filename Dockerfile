# One image for the whole app: the Python backend serves the API and the built screen.

# Stage 1: build the Next.js screen into plain static files.
FROM node:22-slim AS screen
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the backend.
FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/policies ./policies
COPY backend/claims ./claims
COPY backend/samples ./samples
COPY --from=screen /frontend/out ./static

# The host says which port to listen on through PORT; 8000 is the fallback for running the image yourself.
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
