from pymongo import MongoClient
from datetime import datetime

def fetch_documents(start_date_str, end_date_str):
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["your_database_name"]
    collection = db["your_collection_name"]

    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")

    # Define the query
    query = {
        "timestamp": {
            "$gte": start_date,
            "$lt": end_date
        }
    }

    # Execute the query
    results = collection.find(query)

    # Return the results
    return list(results)

# Example usage:
start_date = "2025-01-13T18:30:00.000Z"
end_date = "2025-01-20T18:30:00.000Z"
documents = fetch_documents(start_date, end_date)

for doc in documents:
    print(doc)
