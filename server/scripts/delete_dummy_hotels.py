import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


def main():
    db = get_database()
    demo_prop_ids = [1001, 1002, 1003, 1004, 1005]
    
    r1 = db.dim_hotels.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r2 = db.room_types.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r3 = db.hotel_rooms.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r4 = db.room_inventory_calendar.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r5 = db.rate_plans.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r6 = db.hotel_rate_calendar.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r7 = db.hotel_policies.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r8 = db.hotel_content_pages.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r9 = db.hotel_images.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r10 = db.promotion_campaigns.delete_many({"prop_id": {"$in": demo_prop_ids}})
    r11 = db.coupon_codes.delete_many({"prop_id": {"$in": demo_prop_ids}})

    print("Deleted counts:")
    print(f"  dim_hotels: {r1.deleted_count}")
    print(f"  room_types: {r2.deleted_count}")
    print(f"  hotel_rooms: {r3.deleted_count}")
    print(f"  room_inventory_calendar: {r4.deleted_count}")
    print(f"  rate_plans: {r5.deleted_count}")
    print(f"  hotel_rate_calendar: {r6.deleted_count}")
    print(f"  hotel_policies: {r7.deleted_count}")
    print(f"  hotel_content_pages: {r8.deleted_count}")
    print(f"  hotel_images: {r9.deleted_count}")
    print(f"  promotion_campaigns: {r10.deleted_count}")
    print(f"  coupon_codes: {r11.deleted_count}")

if __name__ == "__main__":
    main()
