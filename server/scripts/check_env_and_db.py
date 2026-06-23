import os, sys
from pymongo import MongoClient

container = sys.argv[1] if len(sys.argv) > 1 else 'unknown'
uri = os.environ.get('MONGO_URI', 'NOT SET')
project_root = os.environ.get('HOTELDATA_PROJECT_ROOT', 'NOT SET')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
print(f'Container: {container}')
print(f'MONGO_URI={uri}')
print(f'HOTELDATA_PROJECT_ROOT={project_root}')
print(f'MONGO_DATABASE={db_name}')

client = MongoClient(uri, serverSelectionTimeoutMS=5000)
dbs = client.list_database_names()
print(f'Databases: {dbs}')

db = client[db_name]
print(f'Collections in {db_name}:')
for c in sorted(db.list_collection_names()):
    print(f'  {c}: {db[c].count_documents({})}')
