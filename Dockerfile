# Use an official Python runtime as a parent image
# TODO lets bump this up dawg, bring all deps up along with it
FROM python:3.12

WORKDIR /app

RUN apt-get update && apt-get install -y iputils-* net-tools curl

# Install Poetry
RUN pip install poetry

# Copy dependency files for layer caching
COPY pyproject.toml poetry.lock README.md /app/

# Copy source code
COPY ./kasa_exporter /app/kasa_exporter

# Install dependencies (including the current project)
RUN poetry config virtualenvs.create false && poetry install --only main


EXPOSE 8000

ENTRYPOINT ["poetry", "run", "python", "-m", "kasa_exporter"]
