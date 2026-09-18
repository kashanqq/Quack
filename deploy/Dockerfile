FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.16 /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy \
    PATH="/srv/quack/backend/.venv/bin:${PATH}"

WORKDIR /srv/quack/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY scripts /srv/quack/scripts
COPY data /srv/quack/data

RUN groupadd --system quack \
    && useradd --system --gid quack --home-dir /home/quack --create-home quack \
    && chown -R quack:quack /srv/quack
USER quack

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
