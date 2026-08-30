import os
os.environ['MONGO_DATABASE'] = 'hoteldata_hub'
from src.database.connection import get_database
db = get_database()
doc = db.booking_orders.find_one({'booking_id': 'BK-20260827142115-6C3CC929'})
print('found', bool(doc))
if doc:
    print('rooms', doc.get('rooms'))
    print('_id', doc.get('_id'), type(doc.get('_id')))
    print('keys', list(doc.keys())[:20])
    # check get_booking_detail
    from src.app.modules.reservations.service.queries import get_booking_detail
    from src.app.core.types import to_json_safe
    detail = get_booking_detail('BK-20260827142115-6C3CC929')
    print('detail keys', list(detail.keys()) if detail else None)
    if detail:
        data = {**detail.get('booking', {}), **detail}
        data.pop('booking', None)
        safe = to_json_safe(data)
        print('safe has _id', '_id' in safe)
        print('safe _id', safe.get('_id'))
        from src.app.modules.reservations.schemas import BookingResponse
        try:
            BookingResponse.model_validate(safe)
            print('validate ok')
        except Exception as e:
            print('validate fail', e)
    # check modify_booking return
    from src.app.modules.reservations.service.lifecycle.create.core import modify_booking
    try:
        res = modify_booking('BK-20260827142115-6C3CC929', comment='test', changed_by='test')
        print('modify_booking returned', res)
        print('has _id', '_id' in res or 'id' in res)
        from src.app.core.types import to_json_safe
        from src.app.modules.reservations.schemas import BookingResponse
        try:
            BookingResponse.model_validate(to_json_safe(res))
            print('modify validate ok')
        except Exception as e:
            print('modify validate fail', e)
    except Exception as e:
        print('modify_booking error', e)
