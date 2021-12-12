ARG PYTHON_VERSION=3.9-slim-buster

# define an alias for the specfic python version used in this file.
FROM python:${PYTHON_VERSION} as python


ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install Poetry Version 1.2.0rc2
ENV POETRY_VERSION=1.2.0rc2
# So that poetry exec can be found on $PATH
ENV PATH="/root/.local/bin:$PATH"


WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg2 dependencies
  libpq-dev \
  # mysqlclient dependencies
  default-libmysqlclient-dev \
  # Translations dependencies
  gettext \
  # to curl
  curl \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

# Requirements are installed here to ensure they will be cached.
COPY pyproject.toml .

# Disable poetry managed virtualenvs and install all dependencies and sub-depenendencies but the project itself
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# copy application code to WORKDIR
COPY . .

# Install dj-stripe package
# dj-stripe is installed later on so that any changes in application code don't cause unnecessary
# re-builds
RUN poetry install --no-interaction --no-ansi --all-extras
