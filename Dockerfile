FROM python:3.12-slim

# Install backend dependencies
COPY web/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy legislative tools (congress_client, legiscan_client, etc.)
COPY legislative-assistant/tools/ /repo/legislative-assistant/tools/

# Copy backend app
COPY web/backend/ /repo/web/backend/

WORKDIR /repo/web/backend

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
