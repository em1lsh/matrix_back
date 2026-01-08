FROM python:3.10-slim AS builder

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.2.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libglib2.0-0 \
        libgthread-2.0-0 \
        libgl1 \
        libglx-mesa0 \
        libxkbcommon0 \
        libxrender1 \
        libxext6 \
        libsm6 \
        libice6 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry
COPY project/pyproject.toml project/poetry.lock /app/
RUN poetry install --no-root --only main



FROM python:3.10-slim

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        libglib2.0-0 \
        libgthread-2.0-0 \
        libgl1 \
        libglx-mesa0 \
        libxkbcommon0 \
        libxrender1 \
        libxext6 \
        libsm6 \
        libice6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g "${APP_GID}" appgroup \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" \
               --create-home --shell /bin/bash appuser

# Копируем установленные зависимости из builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=${APP_UID}:${APP_GID} project/ /app/

USER appuser

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
