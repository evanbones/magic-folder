import time
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import ocrmypdf
import os


INPUT_FOLDER = Path(os.getenv("PDF_INPUT", "/mnt/input_pdfs"))
OUTPUT_FOLDER = Path(os.getenv("PDF_OUTPUT", "/mnt/output_pdfs"))


def ocr_pdf(input_pdf: Path):
    output_pdf = OUTPUT_FOLDER / input_pdf.name
    if output_pdf.exists():
        print(f"Already processed: {input_pdf.name}")
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
        print(f"ERROR {input_pdf.name}: {e}")

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        filepath = Path(event.src_path)
        if filepath.suffix.lower() == '.pdf':
            time.sleep(1)  # Let the file finish copying
            ocr_pdf(filepath)

if __name__ == "__main__":

    print("Scanning existing PDFs...")
    for pdf_file in INPUT_FOLDER.glob("*.pdf"):
        ocr_pdf(pdf_file)

    print("Waiting for new PDFs...")
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INPUT_FOLDER), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
