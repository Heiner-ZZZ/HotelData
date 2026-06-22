from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import RedirectResponse
from src.app.template_utils import templates

from src.app.features.ta02_crud.service import (
    CRUD_COLLECTIONS,
    COLLECTION_LABELS,
    FACT_HOTEL_RESERVATION_COLUMNS,
    SEARCH_FIELDS,
    collection_metadata,
    create_document,
    default_payload,
    delete_document,
    display_columns,
    get_document,
    list_documents,
    update_document,
)


router = APIRouter(prefix="/api", tags=["ta02-crud"])
web_router = APIRouter(tags=["ta02-web-crud"])

FACT_INT_FIELDS = {
    "srch_id",
    "date_key",
    "site_id",
    "visitor_location_country_id",
    "prop_country_id",
    "prop_id",
    "srch_destination_id",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
}

FACT_FLOAT_FIELDS = {
    "visitor_hist_starrating",
    "visitor_hist_adr_usd",
    "prop_starrating",
    "prop_review_score",
    "prop_location_score1",
    "price_usd",
    "reservas_brutas_usd",
}

FACT_BOOL_FIELDS = {
    "prop_brand_bool",
    "promotion_flag",
    "click_bool",
    "reserva_bool",
}

FACT_FIELD_GROUPS = [
    {
        "title": "Identificación del evento",
        "fields": ["source_record_id", "srch_id", "date_time", "date_key", "site_id", "execution_id"],
    },
    {
        "title": "Visitante y hotel",
        "fields": [
            "visitor_location_country_id",
            "visitor_hist_starrating",
            "visitor_hist_adr_usd",
            "prop_country_id",
            "prop_id",
            "prop_starrating",
            "prop_review_score",
            "prop_brand_bool",
            "prop_location_score1",
        ],
    },
    {
        "title": "Reserva y búsqueda",
        "fields": [
            "price_usd",
            "promotion_flag",
            "srch_destination_id",
            "srch_length_of_stay",
            "srch_booking_window",
            "srch_adults_count",
            "srch_children_count",
            "srch_room_count",
            "click_bool",
            "reserva_bool",
            "reservas_brutas_usd",
        ],
    },
    {
        "title": "Categorías derivadas y auditoría",
        "fields": [
            "occupancy_profile_id",
            "stay_length_category_id",
            "booking_window_category_id",
            "price_category_id",
            "loaded_at",
        ],
    },
]


def _guard_collection(collection_name: str) -> None:
    if collection_name not in CRUD_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Collection is not available in TA 02 CRUD")


def _is_fact_collection(collection_name: str) -> bool:
    return collection_name == "fact_hotel_reservations"


def _parse_fact_value(field: str, value: Any) -> Any:
    text = str(value).strip() if value is not None else ""
    if text == "":
        return None
    if field in FACT_BOOL_FIELDS:
        return text.lower() in {"1", "true", "yes", "on", "si", "sí"}
    if field in FACT_INT_FIELDS:
        return int(float(text))
    if field in FACT_FLOAT_FIELDS:
        return float(text)
    return text


def _parse_fact_form(form_data: dict[str, Any]) -> dict[str, Any]:
    return {field: _parse_fact_value(field, form_data.get(field)) for field in FACT_HOTEL_RESERVATION_COLUMNS}


def _crud_form_context(
    *,
    mode: str,
    collection_name: str,
    document_id: str | None,
    payload: str,
    error: str | None,
    form_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fact_form = _is_fact_collection(collection_name)
    values = form_values or (default_payload(collection_name) if fact_form else {})
    return {
        "mode": mode,
        "collection_name": collection_name,
        "collection_label": COLLECTION_LABELS.get(collection_name, collection_name),
        "document_id": document_id,
        "payload": payload,
        "error": error,
        "fact_form": fact_form,
        "field_groups": FACT_FIELD_GROUPS,
        "bool_fields": FACT_BOOL_FIELDS,
        "int_fields": FACT_INT_FIELDS,
        "float_fields": FACT_FLOAT_FIELDS,
        "form_values": values,
    }


@router.get("/collections")
def available_crud_collections() -> dict[str, list[str]]:
    return {"collections": sorted(CRUD_COLLECTIONS)}


@router.get("/{collection_name}")
def list_collection(collection_name: str, page: int = 1, page_size: int = 25, q: str = ""):
    _guard_collection(collection_name)
    return list_documents(collection_name, page, page_size, q)


@router.post("/{collection_name}", status_code=201)
def create_collection_document(collection_name: str, payload: dict[str, Any] = Body(...)):
    _guard_collection(collection_name)
    return create_document(collection_name, payload)


@router.get("/{collection_name}/{document_id}")
def read_collection_document(collection_name: str, document_id: str):
    _guard_collection(collection_name)
    document = get_document(collection_name, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{collection_name}/{document_id}")
def update_collection_document(collection_name: str, document_id: str, payload: dict[str, Any] = Body(...)):
    _guard_collection(collection_name)
    document = update_document(collection_name, document_id, payload)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{collection_name}/{document_id}")
def delete_collection_document(collection_name: str, document_id: str):
    _guard_collection(collection_name)
    return delete_document(collection_name, document_id)


@web_router.get("/ta02")
def ta02_home(request: Request):
    return templates.TemplateResponse(
        request,
        "ta02_crud/home.html",
        {"collections": collection_metadata()},
    )


@web_router.get("/ta02/crud")
def ta02_crud_index(request: Request):
    return templates.TemplateResponse(
        request,
        "ta02_crud/index.html",
        {"collections": collection_metadata()},
    )


@web_router.get("/ta02/crud/{collection_name}")
def ta02_crud_list(request: Request, collection_name: str, page: int = 1, q: str = ""):
    _guard_collection(collection_name)
    results = list_documents(collection_name, page, 25, q)
    return templates.TemplateResponse(
        request,
        "ta02_crud/list.html",
        {
            "collection_name": collection_name,
            "collection_label": COLLECTION_LABELS.get(collection_name, collection_name),
            "search_fields": SEARCH_FIELDS.get(collection_name, []),
            "results": results,
            "display_columns": display_columns(collection_name, results["items"]),
        },
    )


@web_router.get("/ta02/crud/{collection_name}/new")
def ta02_crud_new(request: Request, collection_name: str):
    _guard_collection(collection_name)
    return templates.TemplateResponse(
        request,
        "ta02_crud/form.html",
        _crud_form_context(
            mode="Crear",
            collection_name=collection_name,
            document_id=None,
            payload=json.dumps(default_payload(collection_name), indent=2, ensure_ascii=False),
            error=None,
        ),
    )


@web_router.post("/ta02/crud/{collection_name}/new")
async def ta02_crud_create(request: Request, collection_name: str):
    _guard_collection(collection_name)
    form = await request.form()
    payload = str(form.get("payload", ""))
    form_values = dict(form)
    try:
        document_payload = _parse_fact_form(form_values) if _is_fact_collection(collection_name) else json.loads(payload)
        document = create_document(collection_name, document_payload)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "ta02_crud/form.html",
            _crud_form_context(
                mode="Crear",
                collection_name=collection_name,
                document_id=None,
                payload=payload,
                error=str(exc),
                form_values=form_values,
            ),
            status_code=400,
        )
    return RedirectResponse(f"/ta02/crud/{collection_name}/{document['_id']}", status_code=303)


@web_router.get("/ta02/crud/{collection_name}/{document_id}")
def ta02_crud_detail(request: Request, collection_name: str, document_id: str):
    _guard_collection(collection_name)
    document = get_document(collection_name, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return templates.TemplateResponse(
        request,
        "ta02_crud/detail.html",
        {
            "collection_name": collection_name,
            "collection_label": COLLECTION_LABELS.get(collection_name, collection_name),
            "document": document,
            "display_columns": display_columns(collection_name, [document]),
        },
    )


@web_router.get("/ta02/crud/{collection_name}/{document_id}/edit")
def ta02_crud_edit(request: Request, collection_name: str, document_id: str):
    _guard_collection(collection_name)
    document = get_document(collection_name, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return templates.TemplateResponse(
        request,
        "ta02_crud/form.html",
        _crud_form_context(
            mode="Editar",
            collection_name=collection_name,
            document_id=document_id,
            payload=json.dumps(document, indent=2, ensure_ascii=False),
            error=None,
            form_values=document,
        ),
    )


@web_router.post("/ta02/crud/{collection_name}/{document_id}/edit")
async def ta02_crud_update(request: Request, collection_name: str, document_id: str):
    _guard_collection(collection_name)
    form = await request.form()
    payload = str(form.get("payload", ""))
    form_values = dict(form)
    try:
        document_payload = _parse_fact_form(form_values) if _is_fact_collection(collection_name) else json.loads(payload)
        document = update_document(collection_name, document_id, document_payload)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "ta02_crud/form.html",
            _crud_form_context(
                mode="Editar",
                collection_name=collection_name,
                document_id=document_id,
                payload=payload,
                error=str(exc),
                form_values=form_values,
            ),
            status_code=400,
        )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return RedirectResponse(f"/ta02/crud/{collection_name}/{document_id}", status_code=303)


@web_router.post("/ta02/crud/{collection_name}/{document_id}/delete")
def ta02_crud_delete(collection_name: str, document_id: str):
    _guard_collection(collection_name)
    delete_document(collection_name, document_id)
    return RedirectResponse(f"/ta02/crud/{collection_name}", status_code=303)
