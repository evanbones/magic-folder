# Magic Folder (Image & PDF Automation)

This container automates image cropping/background removal and OCR processing for PDFs.
It’s designed to run using **Docker**, using network-mounted folders for input and output.

---

## Features

* **Image automation**: Automatic cropping, background removal, and export
* **PDF OCR**: Uses `ocrmypdf` and `tesseract` for searchable PDF conversion
* **Automatic folder watching**: Monitors input directories for new files
* **Persistent setup**: Mounts Windows network folders as volumes

---

## Prerequisites

1. **Docker Desktop** installed and configured
2. Access to the network share paths (e.g. `\\VPOHO\Scratch\...`)
3. Ensure Docker Desktop can access network drives:

   * Open **Docker Desktop → Settings → Resources → File Sharing**
   * Add these UNC paths and authenticate:

     ```
     \\VPOHO\Scratch\1. DROP IMAGES HERE
     \\VPOHO\Scratch\2. PROCESSED IMAGES
     \\VPOHO\Scratch\3. DROP PDFS HERE
     \\VPOHO\Scratch\4. PROCESSED PDFS
     ```

---

## Build Instructions

From PowerShell in your project directory:

```powershell
docker build -t magic-folder .
```

---

## Run Instructions

Run the container in background mode, mounting your network folders:

```powershell
docker run -d `
  --name magic-folder `
  --restart unless-stopped `
  -v "\\VPOHO\Scratch\1. DROP IMAGES HERE":/mnt/input_images `
  -v "\\VPOHO\Scratch\2. PROCESSED IMAGES":/mnt/output_images `
  -v "\\VPOHO\Scratch\3. DROP PDFS HERE":/mnt/input_pdfs `
  -v "\\VPOHO\Scratch\4. PROCESSED PDFS":/mnt/output_pdfs `
  magic-folder
```

### Mount Mappings

| Host Folder (Windows)                 | Container Path       | Purpose                 |
| ------------------------------------- | -------------------- | ----------------------- |
| `\\VPOHO\Scratch\1. DROP IMAGES HERE` | `/mnt/input_images`  | Image input folder      |
| `\\VPOHO\Scratch\2. PROCESSED IMAGES` | `/mnt/output_images` | Processed images output |
| `\\VPOHO\Scratch\3. DROP PDFS HERE`   | `/mnt/input_pdfs`    | PDF input folder        |
| `\\VPOHO\Scratch\4. PROCESSED PDFS`   | `/mnt/output_pdfs`   | Processed OCR PDFs      |

---

## Monitoring and Logs

Check container logs in real time:

```powershell
docker logs -f media_processor
```

Stop viewing logs with `Ctrl + C`.

---

## Maintenance Commands

| Action                        | Command                                |
| ----------------------------- | -------------------------------------- |
| Stop the container            | `docker stop magic-folder`             |
| Start it again                | `docker start magic-folder`            |
| Rebuild the image             | `docker build -t magic-folder .`       |
| Remove old container          | `docker rm -f magic-folder`            |
| Shell access inside container | `docker exec -it magic-folder bash`    |

---

## Folder Structure (inside container)

```
/app
 ├── image_autocrop.py
 ├── ocr_pdf.py
 ├── requirements.txt
 └── Dockerfile

/mnt
 ├── input_images/     ← mapped to \\VPOHO\Scratch\1. DROP IMAGES HERE
 ├── output_images/    ← mapped to \\VPOHO\Scratch\2. PROCESSED IMAGES
 ├── input_pdfs/       ← mapped to \\VPOHO\Scratch\3. DROP PDFS HERE
 └── output_pdfs/      ← mapped to \\VPOHO\Scratch\4. PROCESSED PDFS
```

---

## Environment Variables

These are automatically set in the container:

| Variable      | Default              | Description       |
| ------------- | -------------------- | ----------------- |
| `INPUT_ROOT`  | `/mnt/input_images`  | Image input path  |
| `OUTPUT_ROOT` | `/mnt/output_images` | Image output path |
| `PDF_INPUT`   | `/mnt/input_pdfs`    | PDF input path    |
| `PDF_OUTPUT`  | `/mnt/output_pdfs`   | PDF output path   |

---

## Verifying Mounts

To confirm that your UNC shares are accessible inside the container:

```powershell
docker exec -it media_processor bash
ls /mnt/input_images
```

You should see the same files as in `\\VPOHO\Scratch\1. DROP IMAGES HERE`.

---

## License

Intended for internal use only.

This project is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).
