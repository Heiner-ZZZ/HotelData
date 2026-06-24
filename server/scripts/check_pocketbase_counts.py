import requests

def main():
    try:
        auth_url = 'http://localhost:8090/api/collections/_superusers/auth-with-password'
        r = requests.post(auth_url, json={'identity': 'hzambranor@uteq.edu.ec', 'password': 'Heiner2005*'}, timeout=10)
        r.raise_for_status()
        token = r.json().get('token')
        headers = {'Authorization': f'Bearer {token}'}
        
        colls_url = 'http://localhost:8090/api/collections'
        colls = requests.get(colls_url, headers=headers, timeout=10).json().get('items', [])
        
        print("PocketBase collections count:")
        for c in colls:
            name = c['name']
            records_url = f'http://localhost:8090/api/collections/{name}/records?perPage=1'
            total = requests.get(records_url, headers=headers, timeout=10).json().get('totalItems', 0)
            print(f"  - {name}: {total} records")
    except Exception as e:
        print(f"Error querying PocketBase: {e}")

if __name__ == "__main__":
    main()
