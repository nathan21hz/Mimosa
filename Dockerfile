FROM python:3.12-slim

# cron schedules use local time, override with -e TZ=...
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
COPY config.docker.json config.json
# the script may get CRLF line endings when checked out on Windows
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

# external plugins, external/requirements.txt, tasks.json and history.pkl
VOLUME /app/external
EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
