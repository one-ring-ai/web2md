# syntax=docker/dockerfile:1

FROM docker.io/library/python:3.13-alpine3.21

ENV \
    CRYPTOGRAPHY_DONT_BUILD_RUST=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=true \
    UV_SYSTEM_PYTHON=true \
    PYTHONPATH=/app \
    TZ=UTC

USER root
WORKDIR /app

RUN \
    apk add --no-cache \
        bash \
        ca-certificates \
        catatonit \
        coreutils \
        jq \
        smartmontools \
        tzdata \
    && \
    pip install uv

COPY ../requirements.txt ../main.py ./
COPY ../.env .env

RUN uv pip install -r requirements.txt \
    && uv pip install watchgod \
    && mkdir -p /app/data \
    && chown -R nobody:nogroup /app && chmod -R 755 /app \
    && chmod 777 /app/data

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

USER nobody:nogroup

EXPOSE 8000

ENTRYPOINT ["/usr/bin/catatonit", "--", "/entrypoint.sh"]