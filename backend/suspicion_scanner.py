# suspicion_scanner.py
from transformers import pipeline
from datetime import datetime
import random

# Step 1: Simulated user log data
user_logs = {
    "pavan": [
        {"timestamp": "2025-05-29 10:30", "app": "Chrome", "text": "how to hack wifi"},
        {"timestamp": "2025-05-29 10:35", "app": "Discord", "text": "I'm depressed"},
        {"timestamp": "2025-05-29 10:40", "app": "Notepad", "text": "hello world"},
    ],
    "sai": [
        {"timestamp": "2025-05-29 11:00", "app": "WhatsApp", "text": "send me password"},
        {"timestamp": "2025-05-29 11:05", "app": "VSCode", "text": "final project code"},
    ],
    "pranay": [
        {"timestamp": "2025-05-29 09:45", "app": "Telegram", "text": "let's buy drugs"},
        {"timestamp": "2025-05-29 09:50", "app": "Instagram", "text": "funny memes"},
    ]
}

# Step 2: Define blacklisted apps
blacklisted_apps = ["Telegram", "Tor Browser", "Dark Web Browser"]

# Step 3: Load the NLP model
classifier = pipeline("text-classification", model="distilbert-base-uncased", top_k=1)

# Step 4: Analyze and score users
def analyze_user_behavior(logs):
    score = 0
    sus_logs = []
    for log in logs:
        app = log["app"]
        text = log["text"]

        # NLP analysis
        result = classifier(text)
        label = result[0]['label']
        score_val = result[0]['score']

        if label == "NEGATIVE" or "hack" in text.lower() or "drug" in text.lower():
            score += 2
            sus_logs.append(log)

        if app in blacklisted_apps:
            score += 1

    return min(10, score), sus_logs

def get_top_suspicious_users(top_n=3):
    user_scores = []

    for user, logs in user_logs.items():
        score, sus_logs = analyze_user_behavior(logs)
        user_scores.append({
            "user": user,
            "score": score,
            "logs": logs[-5:],  # last 5 logs
            "suspicious_logs": sus_logs
        })

    user_scores.sort(key=lambda x: x["score"], reverse=True)
    return user_scores[:top_n]

# If run directly for testing
if __name__ == "__main__":
    top_users = get_top_suspicious_users()
    for user in top_users:
        print(user)