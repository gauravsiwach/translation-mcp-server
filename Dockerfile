FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app:/app/src
ENV APP_ENV=local
ENV AUTO_CREATE_DB=false
ENV DEFAULT_AI_PROVIDER=openai
ENV OLLAMA_URL=http://host.containers.internal:11434

EXPOSE 8000 8001

# Default CMD runs the FastAPI app.
# Override in docker-compose for the MCP service.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
