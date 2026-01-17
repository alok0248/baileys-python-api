FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y curl gnupg python3 python3-pip python3-venv && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

WORKDIR /app/baileys-server
RUN rm -rf node_modules && npm install && npm install -g tsx

WORKDIR /app/fastapi-server
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app

ENV NODE_PORT=3000 \
    FASTAPI_PORT=3002 \
    FASTAPI_HOST=0.0.0.0

EXPOSE 3000 3002

CMD ["python3", "run_all.py"]
