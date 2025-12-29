# Use lightweight base with Python and OCR dependencies
FROM python:3.11-slim

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    ghostscript \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    poppler-utils \
    cifs-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY image_autocrop.py .
COPY ocr_pdf.py .
COPY start.sh .

# Make start script executable
RUN chmod +x start.sh

# Environment variables
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

ENV INPUT_ROOT=/mnt/data/1.\ DROP\ IMAGES\ HERE \
    OUTPUT_ROOT=/mnt/data/2.\ PROCESSED\ IMAGES \
    PDF_INPUT=/mnt/data/3.\ DROP\ PDFS\ HERE \
    PDF_OUTPUT=/mnt/data/4.\ PROCESSED\ PDFS

# Start via the shell script
CMD ["./start.sh"]