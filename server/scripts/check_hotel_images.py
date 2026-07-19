"""Check hotel images and seed placeholders if missing."""
import os
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

# Find the hotels collection
for col_name in ['hotels', 'properties', 'hotel_properties', 'hotel_content']:
    if col_name in db.list_collection_names():
        docs = list(db[col_name].find({}, {
            '_id': 0, 'prop_id': 1, 'display_name': 1, 'name': 1,
            'image_url': 1, 'images': 1
        }))
        if not docs:
            continue
        print(f'=== {col_name} ({len(docs)} docs) ===')
        for d in docs:
            pid = d.get('prop_id', '?')
            name = d.get('display_name') or d.get('name', '?')
            img = d.get('image_url')
            imgs = d.get('images', [])
            status = 'OK' if (img or imgs) else 'EMPTY'
            print(f'  id={pid} name={name} image_url={img or "NONE"} images_count={len(imgs) if imgs else 0} [{status}]')
        
        empty = db[col_name].count_documents({
            '$or': [
                {'image_url': None}, {'image_url': ''},
                {'image_url': {'$exists': False}},
                {'$and': [
                    {'image_url': {'$exists': False}},
                    {'images': {'$exists': False}}
                ]}
            ]
        })
        print(f'\n  Total docs: {db[col_name].count_documents({})}')
        print(f'  Without any image: {empty}')
        break  # only check first matching collection
else:
    print('No hotel collection found! Available collections:')
    for col in sorted(db.list_collection_names()):
        print(f'  {col}')

c.close()
