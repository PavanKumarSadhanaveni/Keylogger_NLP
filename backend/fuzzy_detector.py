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
    """Loads words from a JSON file, handling the category structure.

    Args:
        filename: The path to the JSON file.

    Returns:
        A dictionary where keys are words and values are their categories,
        or an empty dictionary if the file is not found or invalid.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                word_to_category = {}
                for category, word_list in data.items():
                    if isinstance(word_list, list):
                        for word in word_list:
                            word_to_category[word.strip().lower()] = category
                    else:
                        print(f"Error: Invalid format for category '{category}' in words.json")
                        return {}  # Or handle more gracefully
                return word_to_category
            else:
                print("Error: Invalid JSON format in words.json")
                return {}
    except FileNotFoundError:
        print(f"Error: words.json file not found at {filename}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in words.json")
        return {}

def clean_input(text):
    """Removes non-alphanumeric characters and converts text to lowercase."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower()

def check_word(word, word_to_category, short_threshold=90, long_threshold=80):
    """Checks a single word against a dictionary of words and their categories.

    Args:
        word: The word to check.
        word_to_category: A dictionary where keys are words and values are categories.
        short_threshold: Threshold for short words.
        long_threshold: Threshold for long words.

    Returns:
        A tuple (matched_word, category, ratio) if a match is found,
        or False if no match is found.
    """
    cleaned_word = clean_input(word)
    if not cleaned_word:
        return False

    for bad_word, category in word_to_category.items():
        ratio = fuzz.ratio(cleaned_word, bad_word)
        if len(cleaned_word) <= 4:
            if ratio >= short_threshold:
                return bad_word, category, ratio  # Return category too
        else:
            if ratio >= long_threshold:
                return bad_word, category, ratio  # Return category too
    return False

def detect_bad_words(text, bad_words, threshold=80):
    """Detects bad words in text (kept for compatibility, uses old set-based check)."""
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
    bad_words = load_bad_words()  # Load from badwords.txt (optional)
    words_json = load_words_json()  # Load from words.json

    if not words_json:
        print("No words loaded from words.json. Exiting.")
        return

    test_words = ["apple", "bannana", "orange", "graip", "test", "fck", "ass", "asses", "kys", "marijuana"]
    flagged_words = []

    for word in test_words:
        result = check_word(word, words_json)
        if result:
            matched_word, category, ratio = result
            print(f"Word '{word}' matched '{matched_word}' in category '{category}' with ratio {ratio}.")
            flagged_words.append((word, matched_word, category, ratio))
        else:
            print(f"Word '{word}' did not match.")

    print(f"\nFlagged words: {flagged_words}")

    # --- Example using detect_bad_words (from badwords.txt) ---
    if bad_words:
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