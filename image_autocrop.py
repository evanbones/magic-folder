import os
import time
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import rembg
import threading
from queue import Queue, Empty, PriorityQueue
from dataclasses import dataclass
import psutil
import gc
from typing import Union
from io import BytesIO

INPUT_ROOT = os.getenv("INPUT_ROOT", "/mnt/input_images")
OUTPUT_ROOT = os.getenv("OUTPUT_ROOT", "/mnt/output_images")

SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.tif')

@dataclass
class ResourceConfig:
    max_workers: int = 6
    batch_size: int = 50
    memory_cleanup_interval: int = 300 
    priority_boost: int = 1000
    batch_detection_delay: float = 3.0
    batch_threshold: int = 10

config = ResourceConfig()

rembg_session = None
resource_monitor_lock = threading.Lock()
processing_stats = {"processed": 0, "failed": 0, "start_time": time.time()}
processed_count = 0
processed_count_lock = threading.Lock()

priority_queue = PriorityQueue() 
batch_queue = Queue()
shutdown_event = threading.Event()

def force_memory_cleanup():
    """Force garbage collection and memory cleanup"""
    gc.collect()

def init_rembg():
    """Initialize rembg session"""
    global rembg_session
    if rembg_session is None:
        rembg_session = rembg.new_session('u2net_human_seg')
    return rembg_session

def get_system_resources():
    """Get current system resource usage"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory_percent = psutil.virtual_memory().percent
    available_gb = psutil.virtual_memory().available / (1024**3)
    return cpu_percent, memory_percent, available_gb

class SmartWorkerManager:
    """Manages worker threads with resource monitoring"""
    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.active_workers = 0
        self.lock = threading.Lock()
        self.worker_available = threading.Condition(self.lock)
        
    def acquire_worker(self, priority_boost=False, timeout=None):
        """Try to acquire a worker slot with optional timeout"""
        with self.worker_available:
            if timeout is None:
                while self.active_workers >= self.max_workers:
                    self.worker_available.wait()
                self.active_workers += 1
                return True
            else:
                end_time = time.time() + timeout
                while self.active_workers >= self.max_workers:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return False
                    self.worker_available.wait(timeout=remaining)
                self.active_workers += 1
                return True
    
    def release_worker(self):
        """Release a worker slot"""
        with self.worker_available:
            self.active_workers = max(0, self.active_workers - 1)
            self.worker_available.notify()
    
    def get_active_count(self):
        """Get number of active workers"""
        with self.lock:
            return self.active_workers

worker_manager = SmartWorkerManager(config.max_workers)

def has_transparent_background(im, threshold=0.1):
    """Check if image already has a transparent background"""
    if im.mode != 'RGBA':
        return False
    
    np_img = np.array(im)
    alpha_channel = np_img[:, :, 3]
    
    transparent_pixels = np.sum(alpha_channel < 200)
    total_pixels = alpha_channel.size
    transparent_ratio = transparent_pixels / total_pixels
    
    return transparent_ratio > threshold

def get_background_color(img, sample_size=10):
    """Fast background color detection using corner sampling"""
    h, w = img.shape[:2]
    
    sample_size = min(sample_size, min(h, w) // 4, 10)
    sample_size = max(1, sample_size)
    
    corner_samples = []
    
    corner_samples.append(img[0:sample_size, 0:sample_size, :3])
    corner_samples.append(img[0:sample_size, -sample_size:, :3])
    corner_samples.append(img[-sample_size:, 0:sample_size, :3])
    corner_samples.append(img[-sample_size:, -sample_size:, :3])
    
    all_samples = np.concatenate([corner.reshape(-1, 3) for corner in corner_samples])
    bg_color = np.median(all_samples, axis=0)
    
    return bg_color.astype(np.int32)

def create_mask(img, bg_color, tolerance=20, shadow_factor=1.5):
    """Vectorized mask creation with shadow tolerance"""
    rgb = img[:, :, :3].astype(np.float32)
    bg_color = bg_color.astype(np.float32)
    
    diff = rgb - bg_color
    color_dist = np.sqrt(np.sum(diff * diff, axis=2))
    
    brightness_bg = np.mean(bg_color)
    brightness_img = np.mean(rgb, axis=2)
    
    is_shadow = brightness_img < brightness_bg * 0.7
    adaptive_tolerance = np.where(is_shadow, tolerance * shadow_factor, tolerance)
    
    mask = color_dist > adaptive_tolerance
    
    very_dark = brightness_img < brightness_bg * 0.5
    dark_but_similar_hue = (color_dist > tolerance * 0.6) & very_dark
    mask |= dark_but_similar_hue
    
    if img.shape[2] == 4:
        mask &= (img[:, :, 3] > 10)
    
    return mask

def create_transparent_mask(img):
    """Create mask from alpha channel for transparent images"""
    if img.shape[2] != 4:
        return None
    
    alpha_channel = img[:, :, 3]
    mask = alpha_channel > 10
    
    return mask

def find_best_bbox(mask, min_area=1000, padding=5):
    """Bounding box detection using numpy operations"""
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
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(w, right + padding)
    bottom = min(h, bottom + padding)
    
    return (left, top, right, bottom)

def crop_transparent_background(im, min_area=1000, padding=5):
    """Fast cropping for images with transparent backgrounds"""
    im = im.convert("RGBA")
    np_img = np.array(im)
    
    mask = create_transparent_mask(np_img)
    
    if mask is None:
        return None
    
    content_pixels = np.sum(mask)
    if content_pixels < min_area:
        return None
    
    bbox = find_best_bbox(mask, min_area, padding)
    
    if bbox is None:
        return None
    
    left, top, right, bottom = bbox
    return im.crop((left, top, right, bottom))

def crop_solid_background(im, tolerance=20, shadow_factor=1.5, min_area=1000, padding=5):
    """Fast cropping with basic shadow handling"""
    im = im.convert("RGBA")
    np_img = np.array(im)
    
    bg_color = get_background_color(np_img)
    mask = create_mask(np_img, bg_color, tolerance, shadow_factor)
    
    content_pixels = np.sum(mask)
    if content_pixels < min_area:
        return None
    
    bbox = find_best_bbox(mask, min_area, padding)
    
    if bbox is None:
        return None
    
    left, top, right, bottom = bbox
    return im.crop((left, top, right, bottom))

def remove_background_with_rembg(im: Image.Image, min_area=1000, padding=5) -> Union[Image.Image, None]:
    """Remove background using rembg AI model"""
    try:
        session = init_rembg()
        input_img = im.convert("RGB")
        
        output_data = rembg.remove(input_img, session=session)
        
        if isinstance(output_data, bytes):
            output_img = Image.open(BytesIO(output_data)).convert("RGBA")
        elif isinstance(output_data, np.ndarray):
            output_img = Image.fromarray(output_data).convert("RGBA")
        elif isinstance(output_data, Image.Image):
            output_img = output_data.convert("RGBA")
        else:
            raise TypeError(f"Unexpected rembg output type: {type(output_data)}")
        
        np_img = np.array(output_img)
        
        if np_img.shape[2] == 4:
            mask = np_img[:, :, 3] > 10
        else:
            gray = np.mean(np_img, axis=2)
            mask = gray > 10
        
        if np.sum(mask) < min_area:
            return None
        
        bbox = find_best_bbox(mask, min_area, padding)
        if bbox is None:
            return None
        
        left, top, right, bottom = bbox
        return output_img.crop((left, top, right, bottom))
        
    except Exception as e:
        print(f"rembg processing failed: {e}, falling back to color-based method")
        return None

def should_use_rembg(im):
    """Determine if we should use rembg based on image characteristics"""
    if has_transparent_background(im):
        return False
    
    np_img = np.array(im.convert("RGB"))
    h, w = np_img.shape[:2]
    
    corner_size = min(10, min(h, w) // 10)
    corner_size = max(1, corner_size)
    
    corners = [
        np_img[0:corner_size, 0:corner_size],
        np_img[0:corner_size, -corner_size:],
        np_img[-corner_size:, 0:corner_size],
        np_img[-corner_size:, -corner_size:]
    ]
    
    for corner in corners:
        white_pixels = np.all(corner == [255, 255, 255], axis=2)
        white_ratio = np.sum(white_pixels) / white_pixels.size
        
        if white_ratio > 0.5:
            return False
    
    return True

def crop_to_content(input_path, output_path, is_priority=False):
    """Process a single image with resource management"""
    global processed_count
    
    try:
        # Fixed: Use proper timeout parameter instead of busy-waiting
        max_wait = 30 if is_priority else 300
        
        if not worker_manager.acquire_worker(priority_boost=is_priority, timeout=max_wait):
            print(f"Timeout waiting for worker slot: {input_path}")
            return
        
        try:
            with Image.open(input_path) as im:
                if im.width < 50 or im.height < 50:
                    im.convert("RGBA").save(output_path)
                    print(f"Image too small, saved without cropping: {output_path}")
                    try:
                        os.remove(input_path)
                    except OSError as e:
                        print(f"Could not remove input file {input_path}: {e}")
                    return
                
                cropped = None
                
                if has_transparent_background(im):
                    cropped = crop_transparent_background(im)
                else:
                    use_ai = should_use_rembg(im)
                    if use_ai:
                        cropped = remove_background_with_rembg(im)
                        if cropped is None:
                            cropped = crop_solid_background(im)
                    else:
                        cropped = crop_solid_background(im)
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                if cropped:
                    cropped.save(output_path)
                    status = "Priority" if is_priority else "Batch"
                    print(f"{status} Processed: {os.path.basename(output_path)}")
                    processing_stats["processed"] += 1
                else:
                    im.convert("RGBA").save(output_path)
                    status = "Priority" if is_priority else "Batch"
                    print(f"{status} No crop needed: {os.path.basename(output_path)}")
                    processing_stats["processed"] += 1
                
                try:
                    os.remove(input_path)
                except OSError as e:
                    print(f"Could not remove input file {input_path}: {e}")
                
                # Fixed: Thread-safe counter increment
                with processed_count_lock:
                    processed_count += 1
                    current_count = processed_count
                
                cleanup_interval = config.memory_cleanup_interval // 2 if is_priority else config.memory_cleanup_interval
                if current_count % cleanup_interval == 0:
                    force_memory_cleanup()
                
        finally:
            worker_manager.release_worker()
            
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        processing_stats["failed"] += 1
        if is_priority:
            force_memory_cleanup()

def get_image_priority_score(input_path):
    """Get priority score for image processing (smaller files = higher priority)"""
    try:
        size = os.path.getsize(input_path)
        return size
    except:
        return float('inf')

def priority_processor():
    """Background thread for processing individual priority images"""
    print("Priority processor started")
    
    with ThreadPoolExecutor(max_workers=min(8, config.max_workers // 2)) as executor:
        while not shutdown_event.is_set():
            try:
                priority_score, timestamp, input_path = priority_queue.get(timeout=1.0)
                
                # Fixed: Mark task as done
                try:
                    if not os.path.exists(input_path):
                        continue

                    ext = os.path.splitext(input_path)[1].lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        continue

                    rel_path = os.path.relpath(input_path, INPUT_ROOT)
                    output_path = os.path.join(OUTPUT_ROOT, os.path.splitext(rel_path)[0] + ".png")

                    if not os.path.exists(output_path):
                        executor.submit(crop_to_content, input_path, output_path, True)
                finally:
                    priority_queue.task_done()

            except Empty:
                continue
            except Exception as e:
                print(f"Error in priority processor: {e}")

def collect_batch() -> list:
    """Collect a batch of items from the queue, up to config.batch_size."""
    batch = []
    for _ in range(config.batch_size):
        try:
            item = batch_queue.get(timeout=0.1)
            if os.path.exists(item): 
                batch.append(item)
            # Fixed: Mark task as done
            batch_queue.task_done()
        except Empty:
            break
    return batch

def batch_processor():
    """Background thread for processing batch images."""
    print("Batch processor started")
    
    while not shutdown_event.is_set():
        try:
            batch = collect_batch()

            if not batch:
                time.sleep(1.0)
                continue

            batch.sort(key=get_image_priority_score)

            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                futures = []

                for input_path in batch:
                    ext = os.path.splitext(input_path)[1].lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        continue

                    rel_path = os.path.relpath(input_path, INPUT_ROOT)
                    output_path = os.path.join(OUTPUT_ROOT, os.path.splitext(rel_path)[0] + ".png")

                    if not os.path.exists(output_path):
                        futures.append(
                            executor.submit(crop_to_content, input_path, output_path, False)
                        )

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error processing file in batch: {e}")

            time.sleep(0.2)

        except Exception as e:
            print(f"Error in batch processor: {e}")

def queue_existing_images():
    """Queue existing images for batch processing"""
    print("Scanning for existing images...")
    
    count = 0
    for root, _, files in os.walk(INPUT_ROOT):
        for file in files:
            input_path = os.path.join(root, file)
            ext = os.path.splitext(input_path)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                rel_path = os.path.relpath(input_path, INPUT_ROOT)
                output_path = os.path.join(OUTPUT_ROOT, os.path.splitext(rel_path)[0] + ".png")
                if not os.path.exists(output_path):
                    batch_queue.put(input_path)
                    count += 1
    
    print(f"Queued {count} existing images for batch processing")

class SimpleImageHandler(FileSystemEventHandler):
    """Simplified file system event handler"""
    def __init__(self):
        super().__init__()
        self.pending_files = {}  
        self.file_lock = threading.Lock()
        
        self.pending_processor_thread = threading.Thread(target=self._process_pending_files, daemon=True)
        self.pending_processor_thread.start()
    
    def _process_pending_files(self):
        """Background thread to process pending files and detect batch operations"""
        while not shutdown_event.is_set():
            try:
                time.sleep(0.5)

                current_time = time.time()
                files_to_process = []

                with self.file_lock:
                    if self.pending_files:
                        latest_time = max(self.pending_files.values())
                        if current_time - latest_time >= config.batch_detection_delay:
                            files_to_process = list(self.pending_files.keys())
                            self.pending_files.clear()

                if not files_to_process:
                    continue

                if len(files_to_process) >= config.batch_threshold:
                    print(f"Batch operation detected: {len(files_to_process)} files")
                    for file_path in files_to_process:
                        if os.path.exists(file_path):
                            batch_queue.put(file_path)
                else:
                    for file_path in files_to_process:
                        if os.path.splitext(file_path)[1].lower() in SUPPORTED_EXTENSIONS:
                            priority_score = get_image_priority_score(file_path)
                            timestamp = time.time()
                            priority_queue.put((priority_score, timestamp, file_path))
                            print(f"Individual file queued: {os.path.basename(file_path)}")

            except Exception as e:
                print(f"Error in pending files processor: {e}")
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if os.path.splitext(file_path)[1].lower() not in SUPPORTED_EXTENSIONS:
            return
        
        with self.file_lock:
            self.pending_files[file_path] = time.time()
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if os.path.splitext(file_path)[1].lower() not in SUPPORTED_EXTENSIONS:
            return
        
        with self.file_lock:
            self.pending_files[file_path] = time.time()

if __name__ == "__main__":
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    
    print("Initializing AI background removal model...")
    init_rembg()
    print("AI model loaded successfully!")
    
    print(f"Max workers: {config.max_workers}, Batch size: {config.batch_size}")
    print(f"Batch detection: {config.batch_threshold} files in {config.batch_detection_delay}s")
    
    priority_thread = threading.Thread(target=priority_processor, daemon=True)
    batch_thread = threading.Thread(target=batch_processor, daemon=True)
    
    priority_thread.start()
    batch_thread.start()
    
    queue_existing_images()
    
    print(f"Watching for new files in: {INPUT_ROOT}")
    observer = Observer()
    handler = SimpleImageHandler()
    observer.schedule(handler, path=INPUT_ROOT, recursive=True)
    observer.start()
    
    try:
        last_stats = time.time()
        while True:
            time.sleep(5)
            
            now = time.time()
            if now - last_stats > 60:
                cpu, mem, available_gb = get_system_resources()
                active = worker_manager.get_active_count()
                priority_pending = priority_queue.qsize()
                batch_pending = batch_queue.qsize()
                
                print(f"Stats - CPU: {cpu:.1f}%, Memory: {mem:.1f}%, Available: {available_gb:.1f}GB")
                print(f"Active workers: {active}, Priority queue: {priority_pending}, Batch queue: {batch_pending}")
                print(f"Processed: {processing_stats['processed']}, Failed: {processing_stats['failed']}")
                
                last_stats = now
                
    except KeyboardInterrupt:
        print("\nShutting down...")
        shutdown_event.set()
        observer.stop()
        print("Goodbye!")
    
    observer.join()