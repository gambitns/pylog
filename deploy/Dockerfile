# Chapter 10 — Docker image for pylog.
# The book's Dockerfile is a multi-stage Go build; Python needs only
# one stage: install the dependencies, copy the code, run the agent.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pylog/ ./pylog/
COPY cmd/ ./cmd/

EXPOSE 8401

ENTRYPOINT ["python", "-m", "cmd.agent.main"]
CMD ["--node-id", "node-1", "--data-dir", "/data", "--rpc-addr", "0.0.0.0:8401"]
