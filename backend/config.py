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
    """
    Retrieves settings from the database.
    """
    settings_collection = db.settings
    settings_doc = settings_collection.find_one() # Assuming settings are in a single document

    if settings_doc:
        # Remove the _id field if it exists before returning
        settings_doc.pop('_id', None)
        return settings_doc
    else:
        logging.warning("No settings found in the database. Using default settings.")
        return {} # Return empty dict if no settings found, and let individual functions handle defaults

def update_settings(db, new_settings):
    """Updates email settings in the database."""
    settings_collection = db[SETTINGS_COLLECTION_NAME]
    settings_collection.update_one({"_id": "email_settings"}, {"$set": new_settings}, upsert=True)
    logging.info("Email settings updated.") 