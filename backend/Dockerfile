FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compilation and Chrome
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome/Chromium (with architecture detection)
RUN dpkgArch="$(dpkg --print-architecture)" \
    && case "${dpkgArch##*-}" in \
        amd64) \
            # Install Chrome for AMD64
            wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
            && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
            && apt-get update \
            && apt-get install -y google-chrome-stable \
            ;; \
        arm64) \
            # Install Chromium for ARM64 (Apple Silicon)
            apt-get update \
            && apt-get install -y chromium chromium-driver \
            ;; \
        *) echo "unsupported architecture"; exit 1 ;; \
    esac \
    && rm -rf /var/lib/apt/lists/*

# Install additional dependencies for browser operation and virtual display
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libgbm-dev \
    libasound2 \
    xvfb \
    x11-utils \
    x11-xserver-utils \
    && rm -rf /var/lib/apt/lists/*

# Set browser executable path for Botasaurus based on architecture
RUN dpkgArch="$(dpkg --print-architecture)" \
    && case "${dpkgArch##*-}" in \
        amd64) \
            echo 'export CHROME_EXECUTABLE="/usr/bin/google-chrome"' >> /etc/environment \
            ;; \
        arm64) \
            echo 'export CHROME_EXECUTABLE="/usr/bin/chromium"' >> /etc/environment \
            ;; \
    esac

# 🖥️ Enable server mode for G2 scraping with virtual display
ENV SERVER_MODE=true
ENV DISPLAY=:99

COPY requirements.txt .
RUN pip install --upgrade pip

# Install requirements with preference for pre-built wheels
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy entrypoint scripts first and make them executable
COPY start-server.sh docker-entrypoint.py .
RUN chmod 755 start-server.sh docker-entrypoint.py

# Copy the rest of the application
COPY . .

EXPOSE 8000

# Use startup script to handle virtual display
CMD ["./start-server.sh", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]