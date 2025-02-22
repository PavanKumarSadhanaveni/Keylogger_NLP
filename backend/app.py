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

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"])  # Allow all for SSE

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "keylogger_db"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
words_collection = db["keylogs"]
fs = gridfs.GridFS(db)

KEY_REGEX = re.compile(r'\[.*?\]')
# print(KEY_REGEX.split("This is a [test] string with [multiple] matches."))
KEY_PREFIX = "Key"
MODIFIER_KEYS = ["Ctrl", "Shift", "Alt", "Meta", "Control", "Super"] # You may need to modify this list based on your needs

# --- SSE Queue ---
event_queue = queue.Queue()

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

def _query_database(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Helper function to query the database with given date ranges"""
    query = {
        'timestamp': {
            '$gte': start_date,
            '$lt': end_date
        }
    }
    cursor = words_collection.find(query).sort("timestamp", 1)
    return list(cursor)

@app.route('/api/words', methods=['GET'])
def get_words():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start and end dates are required"}), 400
        
        start_date, end_date = _get_date_range(start_date_str, end_date_str)
        print(f"Received request for words between {start_date} and {end_date}")
        
        words_data = _query_database(start_date, end_date)
        words = _extract_words_from_keys(words_data)
        # print(words)

        print(f"Retrieved {len(words)} words from MongoDB")
        return jsonify(words)

    except ValueError as ve:
        print(f"Error parsing date strings {ve}")
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to retrieve words"}), 500

@app.route('/api/wordcloud', methods=['GET'])
def get_wordcloud():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start and end dates are required"}), 400
        
        start_date, end_date = _get_date_range(start_date_str, end_date_str)
        print(f"Received request for words between {start_date} and {end_date}")
        
        words_data = _query_database(start_date, end_date)
        words = _extract_words_from_keys(words_data)
        word_frequencies = _get_word_frequencies(words)
        
        print(f"Retrieved {len(word_frequencies)} words from MongoDB")
        return jsonify(word_frequencies)
        
    except ValueError as ve:
        print(f"Error parsing date strings {ve}")
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to retrieve words"}), 500

@app.route('/api/fuzzy-matches', methods=['GET'])
def get_fuzzy_matches():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start and end dates are required"}), 400

        start_date, end_date = _get_date_range(start_date_str, end_date_str)
        print(f"Received request for fuzzy matches between {start_date} and {end_date}")

        query = {
            'timestamp': {
                '$gte': start_date,
                '$lt': end_date
            },
            'flags': 'fuzzy_match'
        }
        cursor = words_collection.find(query).sort("timestamp", DESCENDING)
        matches = list(cursor)

        response_data = []
        for match in matches:
            match_data = {}

            # Safely get timestamp
            if 'timestamp' in match:
                match_data['timestamp'] = match['timestamp']
            else:
                match_data['timestamp'] = None  # Or some default value

            # Safely get userId
            if 'userId' in match:
                match_data['userId'] = match['userId']
            else:
                match_data['userId'] = None

            # Safely get flaggedWord
            if 'eventData' in match and 'key' in match['eventData']:
                match_data['flaggedWord'] = match['eventData']['key']
            else:
                match_data['flaggedWord'] = None

            # Safely get flagged_word_similar_to
            if 'flagged_word_similar_to' in match:
                # Handle the case where it's a list (as intended)
                if isinstance(match['flagged_word_similar_to'], list) and match['flagged_word_similar_to']:
                    match_data['flagged_word_similar_to'] = match['flagged_word_similar_to'][0]
                else:
                    match_data['flagged_word_similar_to'] = None
            else:
                match_data['flagged_word_similar_to'] = None


            # Safely get screenshot URL
            if 'screenshot_data' in match and 'screenshot_id' in match['screenshot_data']:
                screenshot_id = match['screenshot_data']['screenshot_id']
                match_data['screenshot_url'] = f"/api/screenshots/{screenshot_id}"
            else:
                match_data['screenshot_url'] = None

            response_data.append(match_data)

        print(f"Retrieved {len(response_data)} fuzzy matches from MongoDB")
        return jsonify(response_data)

    except ValueError as ve:
        print(f"Error parsing date strings: {ve}")
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

    if not all([flagged_word, user_id]):
        return jsonify({'error': 'Missing data'}), 400

    event = {
        "flaggedWord": flagged_word,
        "userId": user_id,
        "screenshotUrl": screenshot_url
    }
    event_queue.put(event)  # Put the event into the queue
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True) # Important: threaded=True for SSE