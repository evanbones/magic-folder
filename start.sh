#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- MAGIC FOLDER STARTUP ---"

# Create the mount point inside the container
mkdir -p /mnt/data

# 2. Mount the network drive directly using env vars
echo "Attempting to mount //VPOHO/Scratch..."
mount -t cifs -o username="$SMB_USER",password="$SMB_PASS",domain="$SMB_DOMAIN",vers=3.0 \
      //VPOHO/Scratch /mnt/data

# Verify the mount
if [ -z "$(ls -A /mnt/data)" ]; then
    echo "CRITICAL ERROR: Mount appears empty. Check credentials or network."
    exit 1
fi

echo "Mount successful. Folders found: $(ls /mnt/data | head -n 3)..."

# Set paths for the Python scripts to use the new mount
export INPUT_ROOT="/mnt/data/1. DROP IMAGES HERE"
export OUTPUT_ROOT="/mnt/data/2. PROCESSED IMAGES"
export PDF_INPUT="/mnt/data/3. DROP PDFS HERE"
export PDF_OUTPUT="/mnt/data/4. PROCESSED PDFS"

# Start the Python scripts in the background
echo "Starting Image Autocrop..."
python3 -u image_autocrop.py &

echo "Starting OCR Processor..."
python3 -u ocr_pdf.py &

# Wait for any process to exit
wait -n
  
# Exit with status of process that exited first
exit $?