from flask import Flask, request, jsonify, Response
from pymongo import MongoClient, DESCENDING
from bson.json_util import dumps
from datetime import datetime, timedelta, timezone
from flask_cors import CORS
import re
from typing import List, Dict
import gridfs
from bson import ObjectId
from io import BytesIO
from flask import send_file
import queue
import time
import json
from dotenv import load_dotenv
import os
from config import get_db, get_settings, update_settings  # Import from config.py
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode
from flask_sslify import SSLify
from dotenv import load_dotenv
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"])  # Allow all for SSE

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "keylogger_db"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
words_collection = db["keylogs"]
email_config_collection = db["email_config"]  # New collection
fs = gridfs.GridFS(db)

KEY_REGEX = re.compile(r'\[.*?\]')
# print(KEY_REGEX.split("This is a [test] string with [multiple] matches."))
KEY_PREFIX = "Key"
MODIFIER_KEYS = ["Ctrl", "Shift", "Alt", "Meta", "Control", "Super"] # You may need to modify this list based on your needs

# --- SSE Queue ---
event_queue = queue.Queue()
def decrypt_data(encrypted_data_base64, key):
    try:
        # Decode the Base64 encoded ciphertext
        ciphertext = b64decode(encrypted_data_base64)

        cipher = AES.new(key, AES.MODE_ECB) # ECB mode, no IV
        decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def encrypt_data(data: str, key: bytes) -> str:
    """Encrypts data using AES in ECB mode (simplified, no IV or salt)."""
    cipher = AES.new(key, AES.MODE_ECB) # ECB mode, no IV
    ciphertext = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    encoded = b64encode(ciphertext).decode('utf-8') # Base64 encode only ciphertext
    return encoded

def derive_key(passphrase: str) -> bytes:
    """Derives a key from a passphrase using SHA256 hash (simplified, no PBKDF2/salt)."""
    hashed_key = SHA256.new(passphrase.encode()).digest() # Hash passphrase directly
    return hashed_key

def _parse_date(date_str: str) -> datetime:
    """Helper function to parse date strings with timezone to UTC"""
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return date.replace(tzinfo=timezone.utc)

def _get_date_range(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    """Helper function to parse date range strings with timezone to UTC and makes the end date inclusive"""
    start_date = _parse_date(start_date_str)
    end_date = _parse_date(end_date_str)
    end_date = end_date + timedelta(days=1)
    return start_date, end_date

def _extract_words_from_keys(words_data: List[Dict]) -> List[str]:
    """Helper function to extract words from keypress data, excluding modifier keys."""
    total_words = []
    for word in words_data:
        key = word.get('eventData', {}).get('key')
        if not key:
            continue
        if key.startswith(KEY_PREFIX):
           continue
        total_words.append(key)
    return total_words

def _get_word_frequencies(words: List[str]) -> List[Dict[str, str]]:
    """Helper to generate word frequency dictionary for word cloud"""
    word_freq = {}
    for word in words:
        if word in word_freq:
            word_freq[word] += 3
        else:
            word_freq[word] = 3
    final_response = []
    for key, value in word_freq.items():
            final_response.append({"text": key, "value": value})
    return final_response

def _query_database(start_date: datetime, end_date: datetime, user_id: str = None) -> List[Dict]:
    """Helper function to query the database with given date ranges and optional user ID"""
    query = {
        'timestamp': {
            '$gte': start_date,
            '$lt': end_date
        }
    }
    if user_id: # Add user ID filter if provided
        query['userId'] = user_id
    cursor = words_collection.find(query).sort("timestamp", 1)
    return list(cursor)

def _fetch_and_process_words(start_date_str, end_date_str, passphrase, processing_function, encrypted_user_id=None):
    """Helper function to fetch words and apply processing, decrypts user_id if provided."""
    if not start_date_str or not end_date_str:
        return jsonify({"error": "Start and end dates required"}), 400

    derived_key = derive_key(passphrase)
    start_date_str = decrypt_data(start_date_str, derived_key)
    end_date_str = decrypt_data(end_date_str, derived_key)
    start_date, end_date = _get_date_range(start_date_str, end_date_str)

    user_id = None # Initialize user_id to None
    if encrypted_user_id: # Decrypt user_id if it's provided and not None
        user_id = decrypt_data(encrypted_user_id, derived_key)
        print(f"Request for user: {user_id}")
    else:
        print(f"Request for all users")

    words_data = _query_database(start_date, end_date, user_id)
    words = _extract_words_from_keys(words_data)
    return processing_function(words, derived_key)

@app.route('/api/words', methods=['GET'])
def get_words():
    def process_words(words, derived_key):
        return jsonify(words)

    encrypted_start_date_str = request.args.get('startDate')
    encrypted_end_date_str = request.args.get('endDate')
    passphrase = request.headers.get('X-Passphrase')
    encrypted_user_id = request.args.get('userId') # Get encrypted userId

    if not passphrase:
        return jsonify({"error": "Passphrase required"}), 401

    try:
        return _fetch_and_process_words(encrypted_start_date_str, encrypted_end_date_str, passphrase, process_words, encrypted_user_id) # Pass encrypted_user_id
    except ValueError as ve:
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to retrieve words"}), 500

@app.route('/api/wordcloud', methods=['GET'])
def get_wordcloud():
    def process_wordcloud(words, derived_key):
        word_frequencies = _get_word_frequencies(words)
        return jsonify(word_frequencies)

    encrypted_start_date_str = request.args.get('startDate')
    encrypted_end_date_str = request.args.get('endDate')
    passphrase = request.headers.get('X-Passphrase')
    encrypted_user_id = request.args.get('userId') # Get encrypted userId

    if not passphrase:
        return jsonify({"error": "Passphrase required"}), 401

    try:
        return _fetch_and_process_words(encrypted_start_date_str, encrypted_end_date_str, passphrase, process_wordcloud, encrypted_user_id) # Pass encrypted_user_id
    except ValueError as ve:
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to retrieve word cloud data"}), 500

@app.route('/api/fuzzy-matches', methods=['GET'])
def get_fuzzy_matches():
    try:
        encrypted_start_date_str = request.args.get('startDate')
        encrypted_end_date_str = request.args.get('endDate')
        passphrase = request.headers.get('X-Passphrase')
        encrypted_user_id = request.args.get('userId') # Get encrypted userId

        if not encrypted_start_date_str or not encrypted_end_date_str:
            return jsonify({"error": "Start and end dates required"}), 400
        if not passphrase:
            return jsonify({"error": "Passphrase required"}), 401

        derived_key = derive_key(passphrase)
        start_date_str = decrypt_data(encrypted_start_date_str, derived_key)
        end_date_str = decrypt_data(encrypted_end_date_str, derived_key)
        start_date, end_date = _get_date_range(start_date_str, end_date_str)

        user_id = None # Initialize user_id to None
        if encrypted_user_id: # Decrypt user_id if it's provided
            user_id = decrypt_data(encrypted_user_id, derived_key)
            print(f"Request for fuzzy matches for user: {user_id}")
        else:
            print(f"Request for fuzzy matches for all users")

        query = {
            'timestamp': {
                '$gte': start_date,
                '$lt': end_date
            },
            'flags': 'fuzzy_match'
        }
        if user_id:
            query['userId'] = user_id
        cursor = words_collection.find(query).sort("timestamp", DESCENDING)
        matches = list(cursor)

        response_data = []
        for match in matches:
            match_data = {}

            if 'timestamp' in match:
                decrypted_timestamp = match['timestamp'].isoformat()
                match_data['timestamp'] = decrypted_timestamp
            else:
                match_data['timestamp'] = None

            if 'userId' in match:
                match_data['userId'] = encrypt_data(match['userId'], derived_key) # Encrypt userId here
            else:
                match_data['userId'] = None

            if 'eventData' in match and 'key' in match['eventData']:
                match_data['flaggedWord'] = match['eventData']['key']
            else:
                match_data['flaggedWord'] = None

            if 'flagged_word_similar_to' in match:
                if isinstance(match['flagged_word_similar_to'], list) and match['flagged_word_similar_to']:
                    match_data['flagged_word_similar_to'] = match['flagged_word_similar_to'][0]
                else:
                    match_data['flagged_word_similar_to'] = None
            else:
                match_data['flagged_word_similar_to'] = None

            if 'category' in match:
                if isinstance(match['category'], list) and match['category']:
                    match_data['category'] = match['category'][0]
                else:
                    match_data['category'] = None
            else:
                match_data['category'] = None

            if 'screenshot_data' in match and 'screenshot_id' in match['screenshot_data']:
                screenshot_id = match['screenshot_data']['screenshot_id']
                match_data['screenshot_url'] = f"/api/screenshots/{screenshot_id}"
            else:
                match_data['screenshot_url'] = None

            response_data.append(match_data)

        return jsonify(response_data)

    except ValueError as ve:
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to retrieve fuzzy matches"}), 500

@app.route('/api/screenshots/<screenshot_id>', methods=['GET'])
def get_screenshot(screenshot_id):
    """Retrieves a screenshot by its GridFS ID and serves it as a file."""
    print(f"attempting to get screenshot: {screenshot_id}")
    try:
        image_data = fs.get(ObjectId(screenshot_id)).read()
        return send_file(BytesIO(image_data), mimetype='image/png')
    except Exception as e:
        print(f"Error retrieving screenshot: {e}")
        return jsonify({"error": "Failed to retrieve screenshot"}), 404

# --- SSE Stream ---
@app.route('/api/stream')
def stream():
    def generate():
        while True:
            event = event_queue.get()  # Wait for an event
            yield f"data: {json.dumps(event)}\n\n"  # Format as SSE
            time.sleep(1) # Prevents the loop from spinning too fast

    return Response(generate(), mimetype='text/event-stream')

# --- Notification Push (called by main.py) ---
@app.route('/api/push_notification', methods=['POST']) # Changed to a route
def push_notification():
    data = request.get_json()
    flagged_word = data.get('flagged_word')
    user_id = data.get('user_id')
    screenshot_url = data.get('screenshot_url')
    passphrase_header = request.headers.get('X-Passphrase') # Get passphrase from headers

    if not all([flagged_word, user_id]):
        return jsonify({'error': 'Missing data'}), 400
    if not passphrase_header:
        return jsonify({"error": "Passphrase required"}), 401

    derived_key = derive_key(passphrase_header)
    encrypted_user_id = encrypt_data(user_id, derived_key) # Encrypt userId before pushing

    event = {
        "flaggedWord": flagged_word,
        "userId": encrypted_user_id, # Use encrypted userId in event
        "screenshotUrl": screenshot_url
    }
    event_queue.put(event)  # Put the event into the queue
    return jsonify({'status': 'success'}), 200

# --- Email Configuration Endpoints ---

@app.route("/api/email_config", methods=["GET"])
def get_email_config():
    """Retrieves the current email configuration."""
    config = email_config_collection.find_one()
    if config:
        # Remove the _id field, as it's not JSON serializable
        config.pop("_id", None)
        return jsonify(config)
    else:
        return jsonify({})  # Return empty object if no config exists


@app.route("/api/email_config", methods=["POST"])
def update_email_config():
    """Updates the email configuration."""
    data = request.get_json()

    # Validate the data (important for security)
    if not all(key in data for key in ["sender_email", "sender_password", "smtp_server", "smtp_port", "recipient_email"]):
        return jsonify({"error": "Missing required fields"}), 400
    if not isinstance(data["smtp_port"], int):
        return jsonify({"error": "smtp_port must be an integer"}), 400

    # Upsert: Update if exists, insert if not
    email_config_collection.update_one({}, {"$set": data}, upsert=True)
    return jsonify({"message": "Email configuration updated successfully"})

@app.route("/api/settings", methods=["GET"])
def get_email_settings():
    """Retrieves email settings."""
    db = get_db()
    settings = get_settings(db)
    # Remove the password before sending it to the frontend
    settings_without_password = {k: v for k, v in settings.items() if k != "sender_password"}
    return jsonify(settings_without_password)

@app.route("/api/settings", methods=["PUT"])
def update_email_settings():
    """Updates email settings."""
    db = get_db()
    new_settings = request.json

    # Basic validation (ensure all fields are present)
    required_fields = ["sender_email", "sender_password", "smtp_server", "smtp_port", "recipient_email"]
    if not all(field in new_settings for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Ensure smtp_port is an integer
    try:
        new_settings['smtp_port'] = int(new_settings['smtp_port'])
    except ValueError:
        return jsonify({"error": "smtp_port must be an integer"}), 400

    update_settings(db, new_settings)
    return jsonify({"message": "Settings updated successfully"})

@app.route("/api/screenshots/<screenshot_id>", methods=["GET"])
def get_screenshot_route(screenshot_id):
    """
    Retrieves and serves a screenshot given its ID.  This integrates
    the screenshot retrieval into the Flask app.
    """
    # Import necessary modules
    import pymongo
    import gridfs
    from bson import ObjectId
    from flask import send_file

    db = get_db()
    fs = gridfs.GridFS(db)

    try:
        # Convert screenshot_id to ObjectId
        screenshot_id = ObjectId(screenshot_id)
        image_data = fs.get(screenshot_id).read()
        return send_file(BytesIO(image_data), mimetype='image/png')
    except Exception as e:
        logging.error(f"Error retrieving screenshot: {e}")
        return jsonify({"error": "Screenshot not found"}), 404

# New endpoint to get unique user IDs
@app.route('/api/users', methods=['GET'])
def get_users():
    """Returns a list of unique user IDs from the keylogs collection, encrypted."""
    unique_user_ids = words_collection.distinct("userId")
    passphrase_header = request.headers.get('X-Passphrase')
    if not passphrase_header:
        return jsonify({"error": "Passphrase required"}), 401
    derived_key = derive_key(passphrase_header)
    encrypted_user_ids = [encrypt_data(userId, derived_key) for userId in unique_user_ids] # Encrypt userIds here
    return jsonify(encrypted_user_ids)

if __name__ == '__main__':
    sslify = SSLify(app)  # Redirect to HTTPS
    app.run(debug=True, host='0.0.0.0', threaded=True) # Important: threaded=True for SSE