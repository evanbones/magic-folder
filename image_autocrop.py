import os
import time
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import rembg
from rembg import remove
import threading
from queue import PriorityQueue, Empty
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import gc

INPUT_ROOT = Path(os.getenv("INPUT_ROOT", "/mnt/data/1. DROP IMAGES HERE"))
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "/mnt/data/2. PROCESSED IMAGES"))

SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.tif')

@dataclass
class Config:
    max_workers: int = 6
    batch_threshold: int = 10
    batch_detection_delay: float = 3.0

config = Config()

# Global resources
executor = ThreadPoolExecutor(max_workers=config.max_workers)
task_queue = PriorityQueue()
shutdown_event = threading.Event()
stats = {"processed": 0, "failed": 0}

def get_priority_score(input_path, is_recent=False):
    """Calculate priority score (lower = higher priority)"""
    try:
        size = input_path.stat().st_size
        return size - 1000000000 if is_recent else size
    except:
        return float('inf')

def has_transparent_background(im, threshold=0.1):
    """Check if image already has a transparent background"""
    if im.mode != 'RGBA':
        return False
    
    alpha = np.array(im)[:, :, 3]
    transparent_ratio = np.sum(alpha < 200) / alpha.size
    return transparent_ratio > threshold

def get_background_color(img, sample_size=10):
    """Detect background color from corners"""
    h, w = img.shape[:2]
    s = min(sample_size, min(h, w) // 4, 10)
    s = max(1, s)
    
    corners = [
        img[0:s, 0:s, :3],
        img[0:s, -s:, :3],
        img[-s:, 0:s, :3],
        img[-s:, -s:, :3]
    ]
    
    all_samples = np.concatenate([c.reshape(-1, 3) for c in corners])
    return np.median(all_samples, axis=0).astype(np.int32)

def create_mask(img, bg_color, tolerance=35):
    """Create mask by detecting non-background pixels"""
    rgb = img[:, :, :3].astype(np.float32)
    bg_color = bg_color.astype(np.float32)
    
    diff = rgb - bg_color
    color_dist = np.sqrt(np.sum(diff * diff, axis=2))
    
    mask = color_dist > tolerance
    
    if img.shape[2] == 4:
        mask &= (img[:, :, 3] > 10)
    
    return mask

def find_bbox(mask, min_area=1000, padding=5):
    """Find bounding box of content"""
    if not np.any(mask):
        return None
    
    rows, cols = np.where(mask)
    
    if len(rows) < min_area:
        return None
    
    top, bottom = rows.min(), rows.max()
    left, right = cols.min(), cols.max()
    
    area = (right - left) * (bottom - top)
    if area < min_area:
        return None
    
    h, w = mask.shape
    return (
        max(0, left - padding),
        max(0, top - padding),
        min(w, right + padding),
        min(h, bottom + padding)
    )

def crop_with_color_detection(im, min_area=1000, padding=5):
    """Crop using color-based background detection"""
    im = im.convert("RGBA")
    np_img = np.array(im)
    
    bg_color = get_background_color(np_img)
    
    tolerance = 25
    
    mask = create_mask(np_img, bg_color, tolerance)
    
    if np.sum(mask) < min_area:
        return None
    
    bbox = find_bbox(mask, min_area, padding)
    if bbox is None:
        return None
    
    return im.crop(bbox)

def crop_with_rembg(im, min_area=1000, padding=5):
    """Remove background using rembg AI model"""
    try:
        input_img = im.convert("RGB")
        
        output_data = rembg.remove(input_img)
        
        if isinstance(output_data, bytes):
            output_img = Image.open(BytesIO(output_data)).convert("RGBA")
        elif isinstance(output_data, np.ndarray):
            output_img = Image.fromarray(output_data).convert("RGBA")
        elif isinstance(output_data, Image.Image):
            output_img = output_data.convert("RGBA")
        else:
            return None
        
        np_img = np.array(output_img)
        mask = np_img[:, :, 3] > 10 if np_img.shape[2] == 4 else np.mean(np_img, axis=2) > 10
        
        if np.sum(mask) < min_area:
            return None
        
        bbox = find_bbox(mask, min_area, padding)
        if bbox is None:
            return None
        
        return output_img.crop(bbox)
        
    except Exception as e:
        print(f"rembg failed: {e}")
        return None

def process_image(input_path, output_path):
    """Process a single image"""
    should_delete = False
    
    try:
        if not input_path.exists():
            return

        with Image.open(input_path) as im:
            im.load() 
            
            if im.width < 50 or im.height < 50:
                im.convert("RGBA").save(output_path)
                should_delete = True
            else:
                cropped = crop_with_color_detection(im)
                
                if cropped is None and not has_transparent_background(im):
                    cropped = crop_with_rembg(im)
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                (im if cropped is None else cropped).convert("RGBA").save(output_path)
                stats["processed"] += 1
                should_delete = True
        
        if should_delete:
            delete_with_retry(input_path)

    except Exception as e:
        print(f"Error processing {input_path.name}: {e}")
        stats["failed"] += 1
    finally:
        gc.collect()

def delete_with_retry(file_path, retries=5, delay=1.0):
    """Attempt to delete a file"""
    import time
    for i in range(retries):
        try:
            if not file_path.exists():
                return
            file_path.unlink()
            return
        except OSError as e:
            if e.errno in (16, 13): 
                time.sleep(delay * (i + 1))
            else:
                print(f"Warning: Could not delete {file_path.name}: {e}")
                break

def worker():
    """Background worker that processes queued tasks"""
    while not shutdown_event.is_set():
        try:
            _priority, input_path = task_queue.get(timeout=1.0)
            
            if input_path is None: 
                task_queue.task_done()
                continue 

            if not input_path.exists():
                task_queue.task_done()
                continue
            
            ext = input_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                task_queue.task_done()
                continue
            
            rel_path = input_path.relative_to(INPUT_ROOT)
            output_path = OUTPUT_ROOT / rel_path.with_suffix('.png')

            if not output_path.exists():
                executor.submit(process_image, input_path, output_path)
            
            task_queue.task_done()
            
        except Empty:
            continue
        except Exception as e:
            print(f"Worker error: {e}")

def queue_existing_images():
    """Queue all existing images for processing"""    
    for file in INPUT_ROOT.rglob('*'):
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            rel_path = file.relative_to(INPUT_ROOT)
            output_path = OUTPUT_ROOT / rel_path.with_suffix('.png')

            if not output_path.exists():
                priority = get_priority_score(file, is_recent=False)
                task_queue.put((priority, file))
        
class ImageHandler(FileSystemEventHandler):
    """Watchdog handler with simple batch detection"""
    def __init__(self):
        super().__init__()
        self.pending = {}
        self.lock = threading.Lock()
        
        threading.Thread(target=self._process_pending, daemon=True).start()
    
    def _process_pending(self):
        """Check for batch operations and queue files"""
        while not shutdown_event.is_set():
            time.sleep(0.5)
            
            with self.lock:
                if not self.pending:
                    continue
                
                current_time = time.time()
                latest_time = max(self.pending.values())
                
                if current_time - latest_time < config.batch_detection_delay:
                    continue
                
                files = list(self.pending.keys())
                self.pending.clear()
            
            is_batch = len(files) >= config.batch_threshold
            for file_path in files:
                if file_path.exists() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    priority = get_priority_score(file_path, is_recent=not is_batch)
                    task_queue.put((priority, file_path))
    
    def _handle_event(self, event):
        """Handle file creation and modification events."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            with self.lock:
                self.pending[path] = time.time()

    def on_created(self, event):
        self._handle_event(event)

    def on_modified(self, event):
        self._handle_event(event)


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    
    worker_thread = threading.Thread(target=worker)
    worker_thread.start()

    queue_existing_images()

    print(f"Watching: {INPUT_ROOT}")

    observer = PollingObserver() 
    observer.schedule(ImageHandler(), path=str(INPUT_ROOT), recursive=True)
    observer.start()
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        shutdown_event.set()
        observer.stop()
        
        task_queue.put((float('inf'), None)) 
        worker_thread.join()
        executor.shutdown(wait=True) 
        print("Goodbye!")
    finally:
        observer.join()