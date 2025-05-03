# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive
ENV STREAMLIT_SERVER_PORT=8501

# Install system dependencies required by Playwright and potentially pandas/other libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libatspi2.0-0 libxkbcommon0 libx11-6 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libpangocairo-1.0-0 \
    libcairo2 libpango-1.0-0 libfontconfig1 libfreetype6 \
    # Other potential dependencies
    build-essential \
    # Clean up
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (only Chromium needed based on your script)
RUN playwright install --with-deps chromium

# Copy the application code into the container
# Make sure all necessary python scripts and config files are copied
COPY app.py .
COPY automation.py .
COPY merge_exchange_rates.py .
COPY config.yaml .

# Expose the Streamlit port
EXPOSE 8501

# Default command to run the Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
