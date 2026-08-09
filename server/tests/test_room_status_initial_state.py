import pytest

from src.app.modules.housekeeping.schemas import RoomStatusLogCreate
from src.app.modules.housekeeping.service.lifecycle.status import upsert_room_status


def test_room_status_initial_state_rejects_unknown_value(db):
    with pytest.raises(ValueError, match="estado de habitación desconocido"):
        upsert_room_status(RoomStatusLogCreate(
            prop_id=720,
            room_type_id="standard",
            room_label="101",
            status="occupied",
        ))

    assert db.room_status_log.count_documents({"prop_id": 720, "room_label": "101"}) == 0
