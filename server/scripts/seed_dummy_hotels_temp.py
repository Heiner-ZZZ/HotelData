from pymongo import MongoClient
import datetime

def main():
    client = MongoClient("mongodb://mongo:27018")
    db = client["hoteldata_hub"]
    now = datetime.datetime.now(datetime.timezone.utc)
    for i in range(1, 6):
        prop_id = 1000 + i
        db.dim_hotels.update_one(
            {"prop_id": prop_id},
            {"$set": {
                "prop_id": prop_id,
                "hotel_name": f"Hotel Demo {prop_id}",
                "hotel_label": f"Hotel Demo {prop_id}",
                "prop_starrating": 4.0,
                "prop_country_id": 1,
                "active": True,
                "description": "Hotel creado para pruebas locales",
                "created_at": now,
                "updated_at": now
            }},
            upsert=True
        )
    print("Seeded dim_hotels successfully on port 27018!")

if __name__ == "__main__":
    main()
