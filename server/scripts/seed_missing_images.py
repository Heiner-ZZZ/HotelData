"""Check which hotels have images and seed placeholder images for those missing."""
import os
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

prop_ids = db.dim_hotels.distinct("prop_id")
print(f"Hotels: {sorted(prop_ids)}\n")

seeded = 0
for pid in sorted(prop_ids):
    count = db.hotel_images.count_documents({"prop_id": pid})
    if count > 0:
        imgs = list(db.hotel_images.find({"prop_id": pid}, {"_id":0, "image_url":1, "title":1}).limit(2))
        urls = [i['image_url'] for i in imgs]
        print(f"  prop_id={pid}: {count} images -> {urls}")
    else:
        print(f"  prop_id={pid}: NO IMAGES - seeding 2 placeholder images...")
        # Seed 2 placeholder images using picsum with unique seeds
        for i in range(1, 3):
            seed = f"hotel{pid}-{i}"
            url = f"https://picsum.photos/seed/{seed}/800/400"
            db.hotel_images.insert_one({
                "prop_id": pid,
                "image_url": url,
                "title": f"Hotel {pid} imagen demo {i}",
                "source": "ga03_operational_seed",
                "demo_seed": True,
            })
            print(f"    Seeded: {url}")
        seeded += 1

print(f"\nSeeded images for {seeded} hotels that were missing them.")
c.close()
