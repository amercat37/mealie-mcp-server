FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies declared in pyproject.toml.
RUN pip install --no-cache-dir \
    "httpx>=0.28.1" \
    "mcp[cli]>=1.12.0" \
    "pydantic>=2.11.3" \
    "python-dotenv>=1.1.0" \
    "joserfc>=1.0.0"

COPY src ./src

EXPOSE 8000

CMD ["python", "src/server.py"]
