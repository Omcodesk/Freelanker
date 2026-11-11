# ContractFlow Python/FastAPI Microservice Container
# Build context must be repository root:
#   docker build -f services/contractflow/Dockerfile -t freelanker-contractflow .

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CONTRACTFLOW_HOST=0.0.0.0 \
    PORT=8000

COPY services/contractflow/requirements.txt /app/services/contractflow/requirements.txt
RUN pip install --no-cache-dir -r /app/services/contractflow/requirements.txt

COPY services /app/services

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn services.contractflow.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
