# Magic Folder (Image & PDF Automation)

This container automates **image cropping/background removal** and **OCR processing for PDFs**.

## Features

* **Image automation**: Automatic cropping, background removal, and export
* **PDF OCR**: Uses `ocrmypdf` + `tesseract` for searchable PDFs
* **Folder watching**: Continuous input monitoring for new files

## Prerequisites

1. **Install Docker Desktop for Windows**
* Download and install from [Docker's official site](https://www.docker.com/products/docker-desktop).
* Ensure **"Use WSL 2 instead of Hyper-V"** is checked.
* In Settings > General, check **"Start Docker Desktop when you log in"**.

2. **Install Ubuntu for WSL**
* Open PowerShell (as Administrator) and run: `wsl --install -d Ubuntu`.

3. **Enable WSL Integration**
* In Docker Desktop Dashboard → Settings → Resources → WSL Integration, toggle the switch for **Ubuntu** to **ON**.


## Initial Setup

1. **Clone/Download** this project into your Windows Documents or a development folder.
2. **Configure Credentials**
Create a file named `.env` in the project root directory and add the required service account credentials:

```env
SMB_USER=YOUR_USERNAME
SMB_PASS=YOUR_PASSWORD
SMB_DOMAIN=YOUR_DOMAIN
```

## Building and Running

Open your WSL (Ubuntu) terminal and navigate to the project folder to start the automation:

```bash
# Navigate to the project directory
cd /mnt/c/Users/{your_username}/Documents/magic-folder

# Build and start the container
docker-compose up -d --build
```

The container will now automatically:

1. Mount `//VPOHO/Scratch` to its internal `/mnt/data` directory.
2. Launch the image and PDF watching scripts.

---

### Folder Mappings (Internal)

The container monitors the following paths on the network share:

| Container Path | Purpose |
| ---            | ---     |
| `/mnt/data/1. DROP IMAGES HERE` | Input images for processing       |
| `/mnt/data/2. PROCESSED IMAGES` | Output for cropped/cleaned images |
| `/mnt/data/3. DROP PDFS HERE`   | Input PDFs for OCR                |
| `/mnt/data/4. PROCESSED PDFS`   | Output for searchable PDFs        |


## Monitoring & Logs

To verify that the network drive mounted successfully and the scripts are running:

```bash
docker logs -f magic-folder
```

**Healthy Startup Log:**
```
> --- MAGIC FOLDER STARTUP ---
> Attempting to mount //VPOHO/Scratch...
> Mount successful. Folders found: 1. DROP IMAGES HERE...
> Starting Image Autocrop...
> Starting OCR Processor...
```

## Maintenance Commands

| Action | Command |
| --- | --- |
| Stop the automation | `docker-compose down` |
| Start automation | `docker-compose up -d` |
| Apply code updates | `docker-compose up -d --build` |
| View real-time logs | `docker logs -f magic-folder` |
| Emergency shell access | `docker exec -it magic-folder bash` |

---

## License

Intended for internal use only. This project is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).