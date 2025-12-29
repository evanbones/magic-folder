import time
import os
from pathlib import Path
from watchdog.observers.polling import PollingObserver 
from watchdog.events import FileSystemEventHandler
import ocrmypdf

INPUT_FOLDER = Path(os.getenv("PDF_INPUT", "/mnt/data/3. DROP PDFS HERE"))
OUTPUT_FOLDER = Path(os.getenv("PDF_OUTPUT", "/mnt/data/4. PROCESSED PDFS"))

def ocr_pdf(input_pdf: Path):
    output_pdf = OUTPUT_FOLDER / input_pdf.name

    if output_pdf.exists():
        print(f"Skipping (already processed): {input_pdf.name}")
        return

    try:
        print(f"Processing: {input_pdf.name}")
        ocrmypdf.ocr(
            input_file=str(input_pdf),
            output_file=str(output_pdf),
            language='eng',
            force_ocr=True
        )
        print(f"OCR complete: {output_pdf.name}")
        
    except Exception as e:
        print(f"ERROR on {input_pdf.name}: {e}")

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(str(event.src_path))
        if filepath.suffix.lower() == '.pdf':
            time.sleep(2) 
            ocr_pdf(filepath)

if __name__ == "__main__":
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    INPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    print(f"Scanning existing PDFs in {INPUT_FOLDER}...")
    for pdf_file in INPUT_FOLDER.glob("*.pdf"):
        ocr_pdf(pdf_file)

    print("Watching for new PDFs...")
    event_handler = PDFHandler()
    
    observer = PollingObserver() 
    observer.schedule(event_handler, str(INPUT_FOLDER), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()