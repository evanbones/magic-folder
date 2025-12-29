# Magic Folder (Image & PDF Automation)

This container automates **image cropping/background removal** and **OCR processing for PDFs**.
It is designed to run using **Docker Desktop for Windows** with the **WSL 2 backend**, accessing files directly from the network share via a Linux mount.


## Features

* **Image automation**: Automatic cropping, background removal, and export
* **PDF OCR**: Uses `ocrmypdf` + `tesseract` for searchable PDFs
* **Folder watching**: Continuous input monitoring for new files



## Prerequisites

1. **Install Docker Desktop for Windows**
   * Download and install from [Docker's official site](https://www.docker.com/products/docker-desktop).
   * During installation, ensure **"Use WSL 2 instead of Hyper-V"** is checked.

2. **Install Ubuntu for WSL**
   Open **PowerShell (as Administrator)** and run:

   ```powershell
   wsl --install -d Ubuntu
   ```

*Follow the prompts to create your UNIX username and password.*

3. **Enable WSL Integration**
   * Open **Docker Desktop Dashboard**.
   * Go to **Settings (Gear Icon) → Resources → WSL Integration**.
   * Toggle the switch for **Ubuntu** to ON.
   * Click **Apply & Restart**.


## One-Time WSL Setup 

For Docker to see the network drive, we must mount the network share using the native Linux SMB protocol (`cifs`).

**Run the following commands inside your WSL (Ubuntu) terminal:**

1. **Install CIFS Utilities:**
```bash
sudo apt update && sudo apt install -y cifs-utils
```

2. **Create the Mount Point:**
```bash
sudo mkdir -p /mnt/p
```


3. **Mount the Drive:**
*Replace `YOUR_USER` and `YOUR_PASS` with your Windows/Network credentials.*
```bash
sudo mount -t cifs -o 'username=YOUR_USERNAME,password=YOUR_PASSWORD,uid=1000,gid=1000' //VPOHO/Scratch /mnt/p
```


4. **Verify the Connection:**
Run `ls -la /mnt/p`. You should see folders like `1. DROP IMAGES HERE`.

### Automate Mount on Startup (Recommended)

To avoid typing the mount command every time you restart WSL, add it to your profile:

1. Open your bash config: `nano ~/.bashrc`
2. Scroll to the bottom and paste this block (replace your credentials):
```bash
# Auto-mount Network Drive for Docker
if [ -z "$(ls -A /mnt/p)" ]; then
    echo "Mounting Magic Folder Drive..."
    sudo mount -t cifs -o 'username=YOUR_USERNAME,password=YOUR_PASSWORD,uid=1000,gid=1000' //VPOHO/Scratch /mnt/p
fi
```

3. Save (Ctrl+O, Enter) and Exit (Ctrl+X).

## Building and Running the Container

Once the drive is mounted at `/mnt/p`, you can run the container from your Ubuntu terminal:

```bash
# Navigate to the project directory
cd /mnt/c/Users/{your_username}/Documents/GitHub/magic-folder

# Build and start the container
docker-compose up -d --build
```

---

### Mount Mappings

| Host Folder (WSL) | Container Path | Purpose |
| --- | --- | --- |
| `/mnt/p/1. DROP IMAGES HERE` | `/mnt/input_images` | Input images |
| `/mnt/p/2. PROCESSED IMAGES` | `/mnt/output_images` | Output images |
| `/mnt/p/3. DROP PDFS HERE` | `/mnt/input_pdfs` | Input PDFs |
| `/mnt/p/4. PROCESSED PDFS` | `/mnt/output_pdfs` | Output PDFs |



## Monitoring & Logs

To see real-time logs:

```bash
docker logs -f magic-folder
```

*(Press `Ctrl + C` to exit)*



## Maintenance Commands

**All commands must be run from WSL Ubuntu terminal:**

| Action | Command |
| --- | --- |
| Stop the container | `docker-compose down` |
| Start it again | `docker-compose up -d` |
| Rebuild the image | `docker-compose up -d --build` |
| Remove the container | `docker-compose down -v` |
| Shell access | `docker exec -it magic-folder bash` |

---

## License

Intended for internal use only.
This project is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).
