# Development image of the backend: the code is mounted from your computer (see docker-compose.yml)
FROM python:3.14-slim
WORKDIR /app

# The code folder is your computer's: no __pycache__ written there by the container's root user
ENV PYTHONDONTWRITEBYTECODE=1

# Dependencies first: Docker reuses this layer while requirements.txt doesn't change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Applies the pending migrations, then starts the API reloading on every change in src
# (only src is watched: a local venv/ in backend/ would be scanned four times a second)
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src"]
