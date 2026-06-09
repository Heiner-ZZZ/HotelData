from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.modules.partner.services import (
    add_partner_hotel_image,
    ensure_hotel_content_collections,
    partner_hotel_content,
    save_partner_hotel_content,
    save_partner_hotel_policies,
)
from src.database.connection import get_database


TEST_PROP_ID = 1
TEST_URL = "https://example.com/ga03-test-hotel-image.jpg"


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    ensure_hotel_content_collections()
    db = get_database()

    before = {
        "hotel_images": db.hotel_images.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_policies": db.hotel_policies.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_content_pages": db.hotel_content_pages.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_content_changes": db.hotel_content_changes.count_documents({"prop_id": TEST_PROP_ID}),
    }

    original_page = db.hotel_content_pages.find_one({"prop_id": TEST_PROP_ID})
    original_policies = db.hotel_policies.find_one({"prop_id": TEST_PROP_ID})
    original_image = db.hotel_images.find_one({"prop_id": TEST_PROP_ID, "image_url": TEST_URL})

    save_partner_hotel_content(
        TEST_PROP_ID,
        description="Contenido de prueba GA03",
        highlights="Vista al mar, lobby renovado",
        amenities_text="Wifi, piscina, desayuno",
        changed_by="validate_ga03_hotel_content",
    )
    save_partner_hotel_policies(
        TEST_PROP_ID,
        check_in_time="15:00",
        check_out_time="12:00",
        cancellation_policy="Cancelación gratuita hasta 24 horas antes.",
        pet_policy="Mascotas pequeñas permitidas.",
        children_policy="Niños menores de 8 años sin cargo adicional.",
        changed_by="validate_ga03_hotel_content",
    )
    add_partner_hotel_image(
        TEST_PROP_ID,
        image_url=TEST_URL,
        title="Imagen de prueba GA03",
        changed_by="validate_ga03_hotel_content",
    )

    detail = partner_hotel_content(TEST_PROP_ID)
    image_doc = db.hotel_images.find_one({"prop_id": TEST_PROP_ID, "image_url": TEST_URL}, {"_id": 0})
    change_count_after = db.hotel_content_changes.count_documents({"prop_id": TEST_PROP_ID})

    # Cleanup controlled changes.
    if original_page is None:
        db.hotel_content_pages.delete_one({"prop_id": TEST_PROP_ID})
    else:
        db.hotel_content_pages.replace_one({"_id": original_page["_id"]}, original_page, upsert=True)

    if original_policies is None:
        db.hotel_policies.delete_one({"prop_id": TEST_PROP_ID})
    else:
        db.hotel_policies.replace_one({"_id": original_policies["_id"]}, original_policies, upsert=True)

    if original_image is None:
        db.hotel_images.delete_one({"prop_id": TEST_PROP_ID, "image_url": TEST_URL})
    else:
        db.hotel_images.replace_one({"_id": original_image["_id"]}, original_image, upsert=True)

    deleted_changes = db.hotel_content_changes.delete_many(
        {"prop_id": TEST_PROP_ID, "changed_by": "validate_ga03_hotel_content"}
    ).deleted_count

    after = {
        "hotel_images": db.hotel_images.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_policies": db.hotel_policies.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_content_pages": db.hotel_content_pages.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_content_changes": db.hotel_content_changes.count_documents({"prop_id": TEST_PROP_ID}),
    }

    report = {
        "ok": bool(detail and image_doc),
        "prop_id": TEST_PROP_ID,
        "before": before,
        "after_save": {
            "description": detail["content_page"]["description"] if detail else None,
            "policy_check_in": detail["policies"]["check_in_time"] if detail else None,
            "images_count": detail["images_count"] if detail else 0,
            "test_image_registered": bool(image_doc),
            "change_count_after": change_count_after,
        },
        "cleanup": {
            "restored_page": original_page is not None,
            "restored_policies": original_policies is not None,
            "restored_image": original_image is not None,
            "deleted_validation_changes": deleted_changes,
        },
        "after_cleanup": after,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
