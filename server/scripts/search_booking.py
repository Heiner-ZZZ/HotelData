import requests
from pymongo import MongoClient

def main():
    booking_id = "BK-20260624043947-9EAC0274"
    print(f"Searching for {booking_id}...")
    
    # 1. MongoDB hoteldata_hub
    client = MongoClient("mongodb://localhost:27018")
    db = client["hoteldata_hub"]
    for coll_name in db.list_collection_names():
        doc = db[coll_name].find_one({"booking_id": booking_id})
        if doc:
            print(f"  [Mongo] Found in collection '{coll_name}': {doc}")
            
    # 2. PocketBase
    try:
        auth_url = 'http://localhost:8090/api/collections/_superusers/auth-with-password'
        r = requests.post(auth_url, json={'identity': 'hzambranor@uteq.edu.ec', 'password': 'Heiner2005*'}, timeout=5)
        token = r.json().get('token')
        headers = {'Authorization': f'Bearer {token}'}
        
        colls = requests.get('http://localhost:8090/api/collections', headers=headers, timeout=5).json().get('items', [])
        for c in colls:
            name = c['name']
            r_search = requests.get(
                f'http://localhost:8090/api/collections/{name}/records',
                params={'filter': f'booking_id="{booking_id}"'},
                headers=headers,
                timeout=5
            )
            items = r_search.json().get('items', [])
            if items:
                print(f"  [PocketBase] Found in collection '{name}': {items[0]}")
    except Exception as e:
        print(f"  [PocketBase] Error: {e}")

if __name__ == "__main__":
    main()
