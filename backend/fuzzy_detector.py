import re
from fuzzywuzzy import fuzz
import json

def load_bad_words(filename="badwords.txt"):
    """Loads bad words from a file (still keeping this for potential use)."""
    try:
        with open(filename, 'r') as f:
            bad_words = {line.strip().lower() for line in f if line.strip()}
            return bad_words
    except FileNotFoundError:
        print(f"Error: Bad words file not found at {filename}")
        return set()

def load_words_json(filename="words.json"):
    """Loads words from a JSON file.

    Args:
        filename: The path to the JSON file.

    Returns:
        A set of words, or an empty set if the file is not found or invalid.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Handle different possible structures of the JSON file
            if isinstance(data, list):
                words = {word.strip().lower() for word in data if isinstance(word, str)}
            elif isinstance(data, dict) and "words" in data:
                words = {word.strip().lower() for word in data["words"] if isinstance(word, str)}
            else:
                print("Error: Invalid JSON format in words.json")
                return set()
            return words
    except FileNotFoundError:
        print(f"Error: words.json file not found at {filename}")
        return set()
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in words.json")
        return set()

def clean_input(text):
    """Removes non-alphanumeric characters and converts text to lowercase."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower()

def check_word(word, word_set, short_threshold=90, long_threshold=80):
    """Checks a single word against a set of words using fuzzy matching.

    Args:
        word: The word to check.
        word_set: A set of words to check against.
        short_threshold: The minimum similarity score (0-100) for short words (<= 4 chars).
        long_threshold: The minimum similarity score (0-100) for long words (> 4 chars).

    Returns:
        True if a match is found above the threshold, False otherwise.
    """
    cleaned_word = clean_input(word)  # Clean the input word
    if not cleaned_word: # if the word is empty after cleaning, return False
        return False

    for bad_word in word_set:
        ratio = fuzz.ratio(cleaned_word, bad_word)
        if len(cleaned_word) <= 4:  # Check if it's a short word
            if ratio >= short_threshold:
                return bad_word,ratio
        else:
            if ratio >= long_threshold:
                return bad_word,ratio
    return False  # Return False if no match is found

def detect_bad_words(text, bad_words, threshold=80):
    """Detects bad words in a given text using fuzzy matching. (Kept for compatibility)"""
    cleaned_text = clean_input(text)
    words = cleaned_text.split()
    matches = []

    for word in words:
        for bad_word in bad_words:
            ratio = fuzz.ratio(word, bad_word)
            if ratio >= threshold:
                matches.append((word, bad_word, ratio))
    return matches

def main():
    """Main function to demonstrate the bad word detection."""

    bad_words = load_bad_words()  # Load bad words from badwords.txt (optional)
    words_json = load_words_json() # Load words from words.json

    if not words_json:
        print("No words loaded from words.json. Exiting.")
        return

    test_words = ["apple", "bannana", "orange", "graip", "test", "fck", "ass", "asses"]
    flagged_words = []

    for word in test_words:
        if check_word(word, words_json):
            print(f"Word '{word}' matched.")
            flagged_words.append(word)
        else:
            print(f"Word '{word}' did not match.")

    print(f"\nFlagged words: {flagged_words}")

    # --- Example using detect_bad_words (from badwords.txt) ---
    if bad_words: # only run if bad_words was loaded successfully
        keylogged_input = "This is some sample input with a few bad w0rds, like sh!t and f*ck."
        print(f"\nInput text (for badwords.txt detection): {keylogged_input}")
        detected = detect_bad_words(keylogged_input, bad_words)

        if detected:
            print("Detected bad words (from badwords.txt):")
            for user_word, bad_word, score in detected:
                print(f"  '{user_word}' matched '{bad_word}' with score: {score}")
        else:
            print("No bad words detected (from badwords.txt).")

if __name__ == "__main__":
    main() 