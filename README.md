# Magic Folder (Image & PDF Automation)

This container automates image cropping/background removal and OCR processing for PDFs.
It’s designed to run using **Docker**, using network-mounted folders for input and output.

-----

## Features

  * **Image automation**: Automatic cropping, background removal, and export
  * **PDF OCR**: Uses `ocrmypdf` and `tesseract` for searchable PDF conversion
  * **Automatic folder watching**: Monitors input directories for new files

-----

## Prerequisites

1.  **Install Docker Desktop:** Download and install it from the official website.
2.  **Install Ubuntu for WSL:** Open **PowerShell (as Administrator)** and run:
    ```powershell
    wsl --install -d Ubuntu
    ```
      * This will install Ubuntu. It will ask you to create a **UNIX username and password**.
3.  **Set Ubuntu as Default WSL Backend:**
    ```powershell
    wsl --set-default Ubuntu
    ```
4.  **Restart Docker Desktop** 

-----

## Setup (One-Time Only)

This container requires a one-time setup script to mount your network drive.

1.  **Clone this repo**

2.  **Enter your Ubuntu terminal:** 

    ```powershell
    wsl
    ```

3.  **Navigate to the project:**

    ```bash
    # Example (change to actual project path):
    cd /mnt/c/Users/{your-username}/Documents/GitHub/magic-folder
    ```

4.  **Prepare and Run the Script:**
    This will install `dos2unix` (to fix Windows file formatting), make the script executable, and run it.

    ```bash
    sudo apt-get update && sudo apt-get install -y dos2unix
    dos2unix setup.sh
    chmod +x setup.sh
    ./setup.sh
    ```

-----

## Building Container

```powershell
docker build -t magic-folder .
```

-----

## Running Container

```powershell
# Stop/Remove any old container
docker rm -f magic-folder

# Run the new container
docker run -d `
  --name magic-folder `
  --restart unless-stopped `
  -v "/mnt/vpoho_scratch/1. DROP IMAGES HERE:/mnt/input_images" `
  -v "/mnt/vpoho_scratch/2. PROCESSED IMAGES:/mnt/output_images" `
  -v "/mnt/vpoho_scratch/3. DROP PDFS HERE:/mnt/input_pdfs" `
  -v "/mnt/vpoho_scratch/4. PROCESSED PDFS:/mnt/output_pdfs" `
  magic-folder
```

### Mount Mappings

| Host Folder (WSL/Ubuntu) | Container Path | Purpose |
| --- | --- | --- |
| `/mnt/vpoho_scratch/1. DROP IMAGES HERE` | `/mnt/input_images` | Image input folder |
| `/mnt/vpoho_scratch/2. PROCESSED IMAGES` | `/mnt/output_images` | Processed images output |
| `/mnt/vpoho_scratch/3. DROP PDFS HERE` | `/mnt/input_pdfs` | PDF input folder |
| `/mnt/vpoho_scratch/4. PROCESSED PDFS` | `/mnt/output_pdfs` | Processed OCR PDFs |

-----

## Monitoring and Logs

Check container logs in real time:

```powershell
docker logs -f magic-folder
```

Stop viewing logs with `Ctrl + C`.

-----

## Maintenance Commands

| Action | Command |
| --- | --- |
| Stop the container | `docker stop magic-folder` |
| Start it again | `docker start magic-folder` |
| Rebuild the image | `docker build -t magic-folder .` |
| Remove old container | `docker rm -f magic-folder` |
| Shell access inside container | `docker exec -it magic-folder bash` |

-----

## Folder Structure (inside container)

```
/app
 ├── image_autocrop.py
 ├── ocr_pdf.py
 ├── requirements.txt
 └── Dockerfile

/mnt
 ├── input_images/ 
 ├── output_images/
 ├── input_pdfs/ 
 └── output_pdfs/
```

-----

## Environment Variables

These are automatically set in the container and point to the container's internal paths.

| Variable | Default | Description |
| --- | --- | --- |
| `INPUT_ROOT` | `/mnt/input_images` | Image input path |
| `OUTPUT_ROOT` | `/mnt/output_images` | Image output path |
| `PDF_INPUT` | `/mnt/input_pdfs` | PDF input path |
| `PDF_OUTPUT` | `/mnt/output_pdfs` | PDF output path |

-----

## License

Intended for internal use only.

This project is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).