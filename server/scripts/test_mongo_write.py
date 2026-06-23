import os
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
print(f'Connecting to {uri}/{db_name}')

client = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = client[db_name]

# Test write
result = db.test_dim_write.insert_one({'test': True, 'source': os.environ.get('HOTELDATA_PROJECT_ROOT', '?')})
print(f'Write OK: {result.inserted_id}')
print(f'Read back: {db.test_dim_write.find_one()}')
db.test_dim_write.drop()
print('Test collection cleaned up')

# Check which collections exist
print(f'All collections: {sorted(db.list_collection_names())}')

# Count actual dim_hotels
print(f'dim_hotels count: {db.dim_hotels.count_documents({})}')
sample = db.dim_hotels.find_one()
if sample:
    print(f'dim_hotels sample keys: {list(sample.keys())}')
