# syntax=docker/dockerfile:1.7

# ---------- builder: install dependencies into /install ----------
FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- runtime: copy only installed deps + app ----------
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Create a non-root user
RUN useradd -m appuser
USER appuser

# Copy only the installed packages from builder (not the whole stdlib)
COPY --from=builder /install /usr/local

# Copy application code
COPY ./src ./src

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
