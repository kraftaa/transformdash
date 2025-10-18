from pymongo import MongoClient

class MongoConnector:
    def __init__(self, uri="mongodb://localhost:27017", dbname="testdb"):
        self.client = MongoClient(uri)
        self.db = self.client[dbname]

    def insert(self, collection_name, document):
        collection = self.db[collection_name]
        return collection.insert_one(document).inserted_id

    def find(self, collection_name, query=None):
        collection = self.db[collection_name]
        return list(collection.find(query or {}))

    def update(self, collection_name, filter_query, update_values):
        collection = self.db[collection_name]
        return collection.update_many(filter_query, {"$set": update_values})

    def delete(self, collection_name, filter_query):
        collection = self.db[collection_name]
        return collection.delete_many(filter_query)

    def close(self):
        self.client.close()

# Usage example
if __name__ == "__main__":
    mongo = MongoConnector()
    mongo.insert("test_collection", {"name": "sample", "value": 123})
    docs = mongo.find("test_collection")
    print(docs)
    mongo.close()
