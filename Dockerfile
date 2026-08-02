FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

# Copy uv binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application
COPY . .

# Final sync to install the project itself if needed
RUN uv sync --frozen --no-dev

CMD ["python", "main.py"]
