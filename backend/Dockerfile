FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compilation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --upgrade pip

# Install requirements with preference for pre-built wheels
RUN pip install --no-cache-dir --prefer-binary -r requirements-docker.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]