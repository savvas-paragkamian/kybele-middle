FROM ubuntu:24.04

ARG VLLM_VERSION=0.17.0
ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:$PATH \
    HF_HOME=/data/huggingface \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv ca-certificates libgomp1 build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && pip install --no-cache-dir "vllm==${VLLM_VERSION}"

WORKDIR /app
COPY serve.sh /app/serve.sh
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/app/serve.sh"]
