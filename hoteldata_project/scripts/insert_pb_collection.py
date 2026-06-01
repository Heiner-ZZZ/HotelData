import sqlite3, json

collection = {
  "id": "pbc_2148885117",
  "system": False,
  "type": "base",
  "name": "hotel_reservation_events__03",
  "fields": [
    {"autogeneratePattern":"[a-z0-9]{15}","help":"","hidden":False,"id":"text3208210256","max":15,"min":15,"name":"id","pattern":"^[a-z0-9]+$","presentable":False,"primaryKey":True,"required":True,"system":True,"type":"text"},
    {"help":"","hidden":False,"id":"number3204872017","max":None,"min":None,"name":"srch_id","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"date1330254257","max":"","min":"","name":"date_time","presentable":False,"required":False,"system":False,"type":"date"},
    {"help":"","hidden":False,"id":"number4139587142","max":None,"min":None,"name":"site_id","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number2500882736","max":None,"min":None,"name":"visitor_location_country_id","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number1561055773","max":None,"min":None,"name":"visitor_hist_starrating","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number1937985758","max":None,"min":None,"name":"visitor_hist_adr_usd","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number648306648","max":None,"min":None,"name":"prop_country_id","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number3736338365","max":None,"min":None,"name":"prop_id","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number2194490170","max":None,"min":None,"name":"prop_starrating","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number2105320430","max":None,"min":None,"name":"prop_review_score","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"bool2909625733","name":"prop_brand_bool","presentable":False,"required":False,"system":False,"type":"bool"},
    {"help":"","hidden":False,"id":"number4244502112","max":None,"min":None,"name":"prop_location_score1","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number3067803474","max":None,"min":None,"name":"price_usd","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"bool1728996101","name":"promotion_flag","presentable":False,"required":False,"system":False,"type":"bool"},
    {"help":"","hidden":False,"id":"number768028753","max":None,"min":None,"name":"srch_destination_id","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number2183811287","max":None,"min":None,"name":"srch_length_of_stay","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number2631242546","max":None,"min":None,"name":"srch_booking_window","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number3595439041","max":None,"min":None,"name":"srch_adults_count","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number3448833554","max":None,"min":None,"name":"srch_children_count","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"number2436746465","max":None,"min":None,"name":"srch_room_count","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"help":"","hidden":False,"id":"bool3124889168","name":"click_bool","presentable":False,"required":False,"system":False,"type":"bool"},
    {"help":"","hidden":False,"id":"bool4115531673","name":"reserva_bool","presentable":False,"required":False,"system":False,"type":"bool"},
    {"help":"","hidden":False,"id":"number1936113795","max":None,"min":None,"name":"reservas_brutas_usd","onlyInt":False,"presentable":False,"required":False,"system":False,"type":"number"},
    {"hidden":False,"id":"autodate2990389176","name":"created","onCreate":True,"onUpdate":False,"presentable":False,"system":False,"type":"autodate"},
    {"hidden":False,"id":"autodate3332085495","name":"updated","onCreate":True,"onUpdate":True,"presentable":False,"system":False,"type":"autodate"}
  ],
  "indexes": [],
  "listRule": None,
  "viewRule": None,
  "createRule": None,
  "updateRule": None,
  "deleteRule": None,
  "options": {}
}

conn = sqlite3.connect('/data/data.db')
cur = conn.cursor()
cur.execute("SELECT 1 FROM _collections WHERE id=?", (collection['id'],))
if cur.fetchone():
    print('collection already exists')
else:
    cur.execute(
        "INSERT INTO _collections (id, system, type, name, fields, indexes, listRule, viewRule, createRule, updateRule, deleteRule, options, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        (
            collection['id'],
            1 if collection['system'] else 0,
            collection['type'],
            collection['name'],
            json.dumps(collection['fields']),
            json.dumps(collection['indexes']),
            collection['listRule'],
            collection['viewRule'],
            collection['createRule'],
            collection['updateRule'],
            collection['deleteRule'],
            json.dumps(collection['options'])
        )
    )
    conn.commit()
    print('inserted collection', collection['name'])
conn.close()
