# Magic Folder (Image & PDF Automation)

This container automates **image cropping/background removal** and **OCR processing for PDFs**.
It's designed to run inside **Docker on WSL (Ubuntu)**, using a **Windows-mapped network drive** for input and output.

---

## Features

* **Image automation**: Automatic cropping, background removal, and export
* **PDF OCR**: Uses `ocrmypdf` + `tesseract` for searchable PDFs
* **Folder watching**: Continuous input monitoring for new files

---

## Prerequisites

1. **Install Docker Desktop for Windows**

   Download and install from [Docker's official site](https://www.docker.com/products/docker-desktop).

2. **Install Ubuntu for WSL**
   Open **PowerShell (as Administrator)** and run:

   ```powershell
   wsl --install -d Ubuntu
   ```

   Set up your UNIX username/password when prompted.

3. **Set Ubuntu as the default WSL backend**

   ```powershell
   wsl --set-default Ubuntu
   ```

4. **Enable WSL integration in Docker Desktop**
   
   Open Docker Desktop → Settings → Resources → WSL Integration
   - Enable "Ubuntu" 
   - Click "Apply & Restart"

5. **Restart Docker Desktop**

---

## One-Time WSL Setup

This container uses a mapped Windows network drive (e.g., `P:`) for input/output.

1. **Ensure your drive is mapped in Windows**
    
    In File Explorer, verify that `P:` points to:

    ```
    \\VPOHO\Scratch
    ```

2. **Mount it in WSL:**
   
   Open a WSL Ubuntu terminal:
   ```bash
   wsl
   ```
   
   Then mount the drive:
   ```bash
   sudo mkdir -p /mnt/p
   sudo mount -t drvfs 'P:' /mnt/p
   ```

   *(Optional — to mount automatically on every WSL start)*

   ```bash
   echo "P: /mnt/p drvfs defaults 0 0" | sudo tee -a /etc/fstab
   ```

3. **Verify it worked:**

   ```bash
   ls /mnt/p
   ```

   You should see your folders like `1. DROP IMAGES HERE`, `2. PROCESSED IMAGES`, etc.

---

## Building and Running the Container

```bash
# Open WSL Ubuntu terminal
wsl

# Navigate to the project directory
cd /mnt/c/Users/{your_username}/Documents/GitHub/magic-folder

# Build and start the container
docker-compose up -d --build
```

---

### Mount Mappings

| Host Folder (WSL)            | Container Path       | Purpose       |
| ---------------------------- | -------------------- | ------------- |
| `/mnt/p/1. DROP IMAGES HERE` | `/mnt/input_images`  | Input images  |
| `/mnt/p/2. PROCESSED IMAGES` | `/mnt/output_images` | Output images |
| `/mnt/p/3. DROP PDFS HERE`   | `/mnt/input_pdfs`    | Input PDFs    |
| `/mnt/p/4. PROCESSED PDFS`   | `/mnt/output_pdfs`   | Output PDFs   |

---

## Monitoring & Logs

To see real-time logs (run from WSL):

```bash
docker logs -f magic-folder
```

*(Press `Ctrl + C` to exit)*

---

## Maintenance Commands

**All commands must be run from WSL Ubuntu terminal:**

| Action               | Command                             |
| -------------------- | ----------------------------------- |
| Stop the container   | `docker-compose down`               |
| Start it again       | `docker-compose up -d`              |
| Rebuild the image    | `docker-compose up -d --build`      |
| Remove the container | `docker-compose down -v`            |
| Shell access         | `docker exec -it magic-folder bash` |
| View logs            | `docker logs -f magic-folder`       |

---

## Folder Layout (inside container)

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

---

## Environment Variables

| Variable      | Default              | Description       |
| ------------- | -------------------- | ----------------- |
| `INPUT_ROOT`  | `/mnt/input_images`  | Image input path  |
| `OUTPUT_ROOT` | `/mnt/output_images` | Image output path |
| `PDF_INPUT`   | `/mnt/input_pdfs`    | PDF input path    |
| `PDF_OUTPUT`  | `/mnt/output_pdfs`   | PDF output path   |

---

## License

Intended for internal use only.

This project is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).

---