"""Pydantic schemas for the legal documents module."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LegalSection(BaseModel):
    heading: str = Field(min_length=1)
    body: str = Field(min_length=1)


class LegalDocumentResponse(BaseModel):
    doc_type: str
    version: int
    title: str
    effective_date: str | None = None
    is_active: bool
    sections: list[LegalSection]
    updated_by: str | None = None


class LegalPublishRequest(BaseModel):
    doc_type: str
    title: str = ""
    sections: list[LegalSection] = Field(min_length=1)
    version: int | None = None
