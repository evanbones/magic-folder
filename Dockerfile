# Use lightweight base with Python and OCR dependencies
FROM python:3.11-slim

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OCRmyPDF and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    ghostscript \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY image_autocrop.py .
COPY ocr_pdf.py .

# Create folders
RUN mkdir -p "/mnt/input_images" "/mnt/output_images" \
    "/mnt/input_pdfs" "/mnt/output_pdfs"

# Environment variables to configure paths
ENV INPUT_ROOT=/mnt/input_images \
    OUTPUT_ROOT=/mnt/output_images \
    PDF_INPUT=/mnt/input_pdfs \
    PDF_OUTPUT=/mnt/output_pdfs

# Start both processors concurrently
CMD ["bash", "-c", "python3 image_autocrop.py & python3 ocr_pdf.py & wait"]