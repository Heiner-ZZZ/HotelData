import sys
from pathlib import Path

import requests
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database

# PB count
r = requests.post('http://pocketbase:8090/api/collections/_superusers/auth-with-password',
    json={'identity':'hzambranor@uteq.edu.ec','password':'Heiner2005*'}, timeout=10)
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}
r2 = requests.get('http://pocketbase:8090/api/collections/hotel_reservation_events_03/records?perPage=1',
    headers=headers, timeout=10)
pb_total = r2.json().get('totalItems', 0)
print(f'PocketBase hotel_reservation_events_03: {pb_total} records')

# MongoDB counts
db = get_database()
print('\nMongoDB hoteldata_hub actual counts:')
dims = ['dim_hotels','dim_destinations','dim_visitor_countries','dim_sites','dim_dates',
        'dim_promotions','dim_click_status','dim_reservation_status','dim_occupancy_profile',
        'dim_stay_length_category','dim_booking_window_category','dim_price_category']
facts = ['fact_hotel_reservations','fact_hotel_events']
for d in dims:
    print(f'  {d}: {db[d].count_documents({})}')
for f in facts:
    print(f'  {f}: {db[f].count_documents({})}')

# Check if there's ANOTHER database
print(f'\nAll databases: {db.client.list_database_names()}')

# Check a sample dimension doc
doc = db.dim_hotels.find_one()
if doc:
    print(f'\nSample dim_hotels: {json.dumps(doc, indent=2, default=str)[:300]}')

doc2 = db.dim_destinations.find_one()
if doc2:
    print(f'\nSample dim_destinations: {json.dumps(doc2, indent=2, default=str)[:300]}')
else:
    print('\ndim_destinations is EMPTY - no docs found')
