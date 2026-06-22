from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from src.app.template_utils import templates

from src.app.features.catalogs.service import (
    catalog_overview,
    create_catalog_item,
    delete_catalog_item,
    list_catalog_items,
    list_catalog_types,
    update_catalog_item,
)


router = APIRouter()


@router.get("/")
def index(request: Request, catalog_type: str = "quality_levels"):
    return templates.TemplateResponse(
        request,
        "catalogs/index.html",
        {
            "selected": catalog_type,
            "catalog_types": list_catalog_types(),
            "overview": catalog_overview(),
            "items": list_catalog_items(catalog_type),
        },
    )


@router.post("/create")
def create(catalog_type: str = Form(...), code: str = Form(...), label: str = Form("")):
    create_catalog_item({"catalog_type": catalog_type, "code": code, "label": label})
    return RedirectResponse(f"/catalogs/?catalog_type={catalog_type}", status_code=303)


@router.post("/update")
def update(catalog_type: str = Form(...), code: str = Form(...), label: str = Form("")):
    update_catalog_item(catalog_type, code, {"label": label})
    return RedirectResponse(f"/catalogs/?catalog_type={catalog_type}", status_code=303)


@router.post("/delete")
def delete(catalog_type: str = Form(...), code: str = Form(...)):
    delete_catalog_item(catalog_type, code)
    return RedirectResponse(f"/catalogs/?catalog_type={catalog_type}", status_code=303)
