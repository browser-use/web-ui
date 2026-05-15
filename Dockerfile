FROM python:3.11-slim-bookworm

# Set platform for multi-arch builds (Docker Buildx will set this)
ARG TARGETPLATFORM
ARG NODE_MAJOR=20

# Install system dependencies (removed libgconf-2-4)
RUN apt-get update && apt-get install -y \
    wget \
    netcat-traditional \
    gnupg \
    curl \
    unzip \
    xvfb \
    libxss1 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-unifont \
    dbus \
    xauth \
    x11vnc \
    tigervnc-tools \
    supervisor \
    net-tools \
    procps \
    git \
    python3-numpy \
    fontconfig \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    vim \
    pipx \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Install Node.js using NodeSource PPA
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verify Node.js and npm installation
RUN node -v && npm -v && npx -v

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install uv and uvx for browser-use
RUN pip install --no-cache-dir uv

# Install Chromium browser for browser-use
RUN apt-get update \
    && apt-get install -y chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome path for browser-use
ENV CHROME_BIN=/usr/bin/chromium
ENV DISPLAY=:99

# Also create a symlink for uvx
RUN ln -s /usr/local/bin/uv /usr/local/bin/uvx || true

# Copy application code
COPY . .

# Set up supervisor configuration and DBus
RUN mkdir -p /var/log/supervisor /run/dbus
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 7788 6080 5901 9222 3000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
