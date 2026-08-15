"""Tests for the read-only guest folio category-id migration plan."""
from __future__ import annotations

import pytest

from scripts.migrate_guest_folios_category_id import (
    _parse_args,
    build_category_lookup,
    plan_posting_updates,
    scan_guest_folios,
)


def test_plans_category_id_for_legacy_labels_and_ids_without_touching_existing_ids():
    lookup = build_category_lookup([
        {"id": "minibar", "label": "Minibar"},
        {"id": "late_checkout", "label": "Late Check-Out"},
    ])
    postings = [
        {"posting_id": "p-label", "category": "Late Check-Out"},
        {"posting_id": "p-id", "category": "minibar"},
        {"posting_id": "p-current", "category": "Minibar", "category_id": "minibar"},
        {"posting_id": "p-unknown", "category": "Otro legado"},
    ]

    planned, skipped = plan_posting_updates(postings, lookup)

    assert planned == [
        {"posting_id": "p-label", "category": "Late Check-Out", "category_id": "late_checkout"},
        {"posting_id": "p-id", "category": "minibar", "category_id": "minibar"},
    ]
    assert skipped == [{"posting_id": "p-unknown", "category": "Otro legado"}]


class _ReadOnlyCursor:
    def __init__(self, documents):
        self.documents = documents

    def limit(self, value):
        return _ReadOnlyCursor(self.documents[:value])

    def __iter__(self):
        return iter(self.documents)


class _ReadOnlyCollection:
    def __init__(self, documents):
        self.documents = documents
        self.query = None
        self.projection = None

    def find(self, query, projection):
        self.query = query
        self.projection = projection
        return _ReadOnlyCursor(self.documents)


def test_scan_is_read_only_and_reports_accent_insensitive_label_matches():
    collection = _ReadOnlyCollection([
        {
            "_id": "folio-1",
            "booking_id": "BK-1",
            "prop_id": 1,
            "postings": [{"posting_id": "p1", "category": "Habitación"}],
        },
    ])
    lookup = build_category_lookup([{"id": "habitacion", "label": "Habitación"}])

    report = scan_guest_folios(collection, lookup, prop_id=1)

    assert report["postings_would_update"] == 1
    assert report["folios"][0]["planned"] == [
        {"posting_id": "p1", "category": "Habitación", "category_id": "habitacion"},
    ]
    assert collection.query["prop_id"] == 1
    assert "update_one" not in collection.__dict__


def test_dry_run_acknowledgement_is_required():
    with pytest.raises(SystemExit):
        _parse_args([])

    args = _parse_args(["--dry-run", "--skip-seed-source"])
    assert args.dry_run is True
