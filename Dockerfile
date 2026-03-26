FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Re-install with source
RUN pip install --no-cache-dir .

# Create data directory
RUN mkdir -p /root/.t9os_data /root/.config/t9os

ENTRYPOINT ["t9"]
CMD ["daily"]
