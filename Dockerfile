# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the frontend
COPY frontend/ ./

# Build Next.js (output goes to out/)
RUN npm run build

# Stage 2: Serve with FastAPI
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Copy backend code
COPY backend/ ./

# Copy built frontend to backend static directory (replacing any placeholder)
RUN rm -rf ./static/* || true
COPY --from=frontend-builder /app/out ./static/

# Expose port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
