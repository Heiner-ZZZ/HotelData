from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from src.app.features.ta02_crud.service import (
    CRUD_COLLECTIONS,
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)


router = APIRouter(prefix="/api", tags=["ta02-crud"])


def _guard_collection(collection_name: str) -> None:
    if collection_name not in CRUD_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Collection is not available in TA 02 CRUD")


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
