FROM python:3.13-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Cloud Run injects $PORT at runtime; default to 4555 for local dev.
ENV PORT=4555
EXPOSE 4555

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT}
