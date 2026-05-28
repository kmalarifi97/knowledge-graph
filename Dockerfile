FROM python:3.11-slim

# Deterministic, no network surprises at run time.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Source is bind-mounted in dev (see docker-compose.yml). For ad-hoc runs
# without compose we still copy so the image is self-contained.
COPY . .

# Default to running the full pipeline. Override with `docker run ... bash`
# or `make sh` for an interactive shell.
CMD ["python", "-m", "pipeline"]
