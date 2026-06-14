from __future__ import annotations

from urllib.parse import urlencode

from fastapi import HTTPException, Request, status as http_status


def page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    return f"{request.url.path}?{urlencode(params)}"


def require_prop_id(prop_id: int | None) -> int:
    if prop_id is None or prop_id <= 0:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="prop_id is required")
    return prop_id
