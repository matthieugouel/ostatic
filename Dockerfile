FROM tiangolo/uvicorn-gunicorn:latest
LABEL key="Matthieu Gouel <matthieu.gouel@protonmail.fr>"

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml pyproject.toml
RUN poetry install --no-root --no-dev

COPY main.py main.py
