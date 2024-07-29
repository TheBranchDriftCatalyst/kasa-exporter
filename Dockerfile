# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

RUN apt-get update

RUN apt-get install iputils-* -y
RUN apt-get install net-tools -y

# Install Poetry
RUN pip install poetry

# Copy only the pyproject.toml and poetry.lock files to leverage Docker cache
COPY pyproject.toml poetry.lock readme.md /app/

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --no-dev

# Copy the current directory contents into the container at /app
COPY . /app

# Expose the port that the app runs on
EXPOSE 8000

# Set the entry point to run the exporter module
ENTRYPOINT ["poetry", "run", "python", "-m", "kasa_exporter.exporter"]

# TODO: we need to do somethign about multicast broadcasting accross the container network boundary. 
# Kasa discover does this to discover iot devices.
