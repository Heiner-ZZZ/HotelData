from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.database.connection import get_database


PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "mongodb_model_audit.json"
MARKDOWN_REPORT_PATH = PROJECT_ROOT / "docs" / "ga03" / "mongodb_model_audit.md"

FACT_COLLECTION = "fact_hotel_reservations"
RELATION_SPECS = [
    ("prop_id", "dim_hotels", "prop_id"),
    ("srch_destination_id", "dim_destinations", "srch_destination_id"),
    ("visitor_location_country_id", "dim_visitor_countries", "visitor_location_country_id"),
    ("site_id", "dim_sites", "site_id"),
    ("date_key", "dim_dates", "date_key"),
    ("occupancy_profile_id", "dim_occupancy_profile", "occupancy_profile_id"),
    ("stay_length_category_id", "dim_stay_length_category", "stay_length_category_id"),
    ("booking_window_category_id", "dim_booking_window_category", "booking_window_category_id"),
    ("price_category_id", "dim_price_category", "price_category_id"),
]
DISPLAY_SPECS = {
    "dim_hotels": ["display_name", "hotel_name", "hotel_label"],
    "dim_destinations": ["destination_display_name", "destination_name", "destination_label"],
    "dim_visitor_countries": ["country_display_name", "country_name", "visitor_country_label"],
    "dim_sites": ["site_display_name", "site_name", "site_label"],
}
CLASSIFICATION_ORDER = [
    "Activa",
    "Seguridad activa",
    "Gobierno de datos",
    "Operativa parcial",
    "Preparada sin datos",
    "Legacy/compatibilidad",
    "Legacy sin uso",
]
SECURITY_COLLECTIONS = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_sessions",
    "user_activity_logs",
}
GOVERNANCE_COLLECTIONS = {
    "etl_executions",
    "data_quality_reports",
    "rejected_records",
    "system_catalogs",
}
ACTIVE_MODEL_COLLECTIONS = {
    "fact_hotel_reservations",
    "dim_hotels",
    "dim_destinations",
    "dim_visitor_countries",
    "dim_sites",
    "dim_dates",
    "dim_occupancy_profile",
    "dim_stay_length_category",
    "dim_booking_window_category",
    "dim_price_category",
    "dim_promotions",
    "dim_reservation_status",
    "dim_click_status",
}
LEGACY_COMPAT_COLLECTIONS = {
    "fact_hotel_events",
    "dataset_container",
}
LEGACY_CANDIDATE_EMPTY_COLLECTIONS = {
    "dim_date",
    "dim_countries",
}
PARTIAL_OPERATIONAL_COLLECTIONS = {
    "hotels",
    "locations",
    "contacts",
    "websites",
    "facilities",
    "attractions",
    "search_logs",
    "hotel_quality",
    "hotel_content_changes",
    "booking_orders",
    "booking_guests",
    "booking_status_history",
}
PREPARED_COLLECTIONS = {
    "blackout_dates",
    "coupon_codes",
    "hotel_content_pages",
    "hotel_images",
    "hotel_policies",
    "hotel_rate_calendar",
    "hotel_rooms",
    "manual_reservations",
    "promotion_campaigns",
    "rate_plans",
    "rate_rules",
    "room_availability_blocks",
    "room_inventory_calendar",
    "room_types",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [clean_value(item) for item in value[:8]]
    if isinstance(value, dict):
        return {str(key): clean_value(val) for key, val in list(value.items())[:12]}
    return str(value)


def sample_documents(collection, limit: int = 3) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for item in collection.find({}, {"_id": 0}).limit(limit):
        samples.append({key: clean_value(value) for key, value in item.items()})
    return samples


def sample_fields(collection, limit: int = 20) -> list[str]:
    fields: set[str] = set()
    for item in collection.find({}, {"_id": 0}).limit(limit):
        fields.update(item.keys())
    return sorted(fields)


def non_empty_filter(field_name: str) -> dict[str, Any]:
    return {
        field_name: {
            "$exists": True,
            "$nin": [None, "", [], {}],
        }
    }


def collection_reference_counts(project_root: Path, collection_names: list[str]) -> dict[str, int]:
    search_roots = [
        project_root / "server" / "src",
        project_root / "server" / "scripts",
        project_root / "frontend" / "src",
        project_root / "docs" / "ga03",
    ]
    allowed_ext = {".py", ".ts", ".html", ".scss", ".md", ".json", ".yml", ".yaml"}
    counts = {name: 0 for name in collection_names}
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in allowed_ext:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for name in collection_names:
                if name in text:
                    counts[name] += 1
    return counts


def relation_coverage(db, fact_collection: str, fact_field: str, dim_collection: str, dim_field: str) -> dict[str, Any]:
    fact = db[fact_collection]
    dim = db[dim_collection]
    total_fact_rows = fact.estimated_document_count()
    fact_rows_with_key = fact.count_documents(non_empty_filter(fact_field))
    fact_rows_without_key = total_fact_rows - fact_rows_with_key
    dim_total_rows = dim.estimated_document_count()

    pipeline = [
        {"$match": non_empty_filter(fact_field)},
        {"$group": {"_id": f"${fact_field}", "fact_rows": {"$sum": 1}}},
        {
            "$lookup": {
                "from": dim_collection,
                "localField": "_id",
                "foreignField": dim_field,
                "as": "dim_match",
            }
        },
        {
            "$project": {
                "_id": 1,
                "fact_rows": 1,
                "matched": {"$gt": [{"$size": "$dim_match"}, 0]},
            }
        },
        {
            "$group": {
                "_id": "$matched",
                "distinct_keys": {"$sum": 1},
                "fact_rows": {"$sum": "$fact_rows"},
            }
        },
    ]
    grouped = list(fact.aggregate(pipeline, allowDiskUse=True))
    matched = next((item for item in grouped if item["_id"] is True), {})
    missing = next((item for item in grouped if item["_id"] is False), {})

    missing_sample_pipeline = [
        {"$match": non_empty_filter(fact_field)},
        {"$group": {"_id": f"${fact_field}", "fact_rows": {"$sum": 1}}},
        {
            "$lookup": {
                "from": dim_collection,
                "localField": "_id",
                "foreignField": dim_field,
                "as": "dim_match",
            }
        },
        {"$match": {"dim_match": {"$eq": []}}},
        {"$sort": {"fact_rows": -1, "_id": 1}},
        {"$limit": 10},
    ]
    missing_key_samples = [
        {"key": clean_value(item["_id"]), "fact_rows": item["fact_rows"]}
        for item in fact.aggregate(missing_sample_pipeline, allowDiskUse=True)
    ]

    distinct_fact_keys = int(matched.get("distinct_keys", 0) + missing.get("distinct_keys", 0))
    matched_fact_rows = int(matched.get("fact_rows", 0))
    missing_fact_rows = int(missing.get("fact_rows", 0))
    missing_distinct_keys = int(missing.get("distinct_keys", 0))
    matched_distinct_keys = int(matched.get("distinct_keys", 0))

    row_coverage_ratio = matched_fact_rows / fact_rows_with_key if fact_rows_with_key else 0.0
    distinct_coverage_ratio = matched_distinct_keys / distinct_fact_keys if distinct_fact_keys else 0.0

    return {
        "fact_collection": fact_collection,
        "fact_field": fact_field,
        "dimension_collection": dim_collection,
        "dimension_field": dim_field,
        "fact_total_rows": total_fact_rows,
        "fact_rows_with_key": fact_rows_with_key,
        "fact_rows_without_key": fact_rows_without_key,
        "dimension_total_rows": dim_total_rows,
        "distinct_fact_keys": distinct_fact_keys,
        "matched_distinct_keys": matched_distinct_keys,
        "missing_distinct_keys": missing_distinct_keys,
        "matched_fact_rows": matched_fact_rows,
        "missing_fact_rows": missing_fact_rows,
        "row_coverage_ratio": round(row_coverage_ratio, 6),
        "distinct_coverage_ratio": round(distinct_coverage_ratio, 6),
        "is_complete": fact_rows_without_key == 0 and missing_fact_rows == 0,
        "missing_key_samples": missing_key_samples,
    }


def display_audit(db, collection_name: str, fields: list[str]) -> dict[str, Any]:
    collection = db[collection_name]
    total_rows = collection.estimated_document_count()
    field_metrics: dict[str, Any] = {}
    available_display_fields: list[str] = []
    missing_display_fields: list[str] = []

    for field_name in fields:
        non_empty = collection.count_documents(non_empty_filter(field_name))
        available = non_empty > 0
        if available:
            available_display_fields.append(field_name)
        else:
            missing_display_fields.append(field_name)
        field_metrics[field_name] = {
            "non_empty_count": non_empty,
            "coverage_ratio": round((non_empty / total_rows), 6) if total_rows else 0.0,
            "available": available,
        }

    discovered_fields = [
        field_name
        for field_name in sample_fields(collection, limit=25)
        if "display" in field_name or field_name.endswith("_label") or field_name.endswith("_name") or field_name == "name"
    ]
    return {
        "collection": collection_name,
        "total_rows": total_rows,
        "expected_fields": fields,
        "available_display_fields": available_display_fields,
        "missing_display_fields": missing_display_fields,
        "field_metrics": field_metrics,
        "discovered_display_like_fields": sorted(discovered_fields),
        "sample_documents": sample_documents(collection, limit=2),
    }


def collection_status(
    collection_name: str,
    count: int,
    reference_count: int,
) -> tuple[str, str]:
    if collection_name in SECURITY_COLLECTIONS:
        return "Seguridad activa", "Colección usada por autenticación, roles, sesiones o auditoría de usuarios."
    if collection_name in GOVERNANCE_COLLECTIONS:
        return "Gobierno de datos", "Colección orientada a control de calidad, ejecución ETL o catálogos transversales."
    if collection_name in ACTIVE_MODEL_COLLECTIONS and count > 0:
        return "Activa", "Parte del modelo GA03 actualmente poblado y usado por consultas o navegación."
    if collection_name in LEGACY_CANDIDATE_EMPTY_COLLECTIONS:
        return "Legacy/compatibilidad", "Colección heredada del modelo anterior, vacía y candidata a marcarse como legacy."
    if collection_name in LEGACY_COMPAT_COLLECTIONS:
        if count > 0:
            return "Legacy/compatibilidad", "Mantiene compatibilidad con flujos o artefactos anteriores al modelo GA03 vigente."
        return "Legacy sin uso", "Colección legacy sin datos activos."
    if collection_name in PARTIAL_OPERATIONAL_COLLECTIONS:
        return "Operativa parcial", "Colección operativa con datos o estructura parcial, útil pero no completa."
    if collection_name in PREPARED_COLLECTIONS:
        if count == 0:
            return "Preparada sin datos", "Colección prevista para módulos operativos futuros, aún sin poblar."
        return "Operativa parcial", "Colección operativa preparada con datos parciales."
    if count == 0 and reference_count > 0:
        return "Preparada sin datos", "Existe referencia en código pero todavía no tiene población real."
    if count == 0:
        return "Legacy sin uso", "No tiene datos ni señales claras de uso activo."
    return "Operativa parcial", "Tiene datos, pero no pertenece al núcleo GA03 ni al bloque de seguridad/gobierno."


def build_collection_audit(db) -> dict[str, Any]:
    collection_names = sorted(db.list_collection_names())
    reference_counts = collection_reference_counts(PROJECT_ROOT, collection_names)
    audits: list[dict[str, Any]] = []

    for name in collection_names:
        collection = db[name]
        count = int(collection.estimated_document_count())
        fields = sample_fields(collection)
        classification, rationale = collection_status(name, count, reference_counts.get(name, 0))
        audits.append(
            {
                "name": name,
                "count": count,
                "classification": classification,
                "classification_rationale": rationale,
                "reference_count": reference_counts.get(name, 0),
                "sample_fields": fields,
                "sample_documents": sample_documents(collection, limit=2),
            }
        )

    counts_by_classification = Counter(item["classification"] for item in audits)
    return {
        "collections": audits,
        "counts_by_classification": {key: counts_by_classification.get(key, 0) for key in CLASSIFICATION_ORDER},
    }


def build_fact_metrics(db) -> dict[str, Any]:
    fact = db[FACT_COLLECTION]
    total_rows = fact.estimated_document_count()
    return {
        "total_rows": total_rows,
        "click_bool_true": fact.count_documents({"click_bool": True}),
        "reserva_bool_true": fact.count_documents({"reserva_bool": True}),
        "reservas_brutas_usd_positive": fact.count_documents({"reservas_brutas_usd": {"$gt": 0}}),
        "promotion_flag_true": fact.count_documents({"promotion_flag": True}),
    }


def recommendation_block(
    relation_results: list[dict[str, Any]],
    display_results: list[dict[str, Any]],
    collections: list[dict[str, Any]],
) -> dict[str, Any]:
    complete_relations = [
        f"{item['fact_field']} -> {item['dimension_collection']}.{item['dimension_field']}"
        for item in relation_results
        if item["is_complete"]
    ]
    incomplete_relations = [
        {
            "relation": f"{item['fact_field']} -> {item['dimension_collection']}.{item['dimension_field']}",
            "missing_fact_rows": item["missing_fact_rows"],
            "missing_distinct_keys": item["missing_distinct_keys"],
        }
        for item in relation_results
        if not item["is_complete"]
    ]
    missing_display_fields = [
        {
            "collection": item["collection"],
            "fields": item["missing_display_fields"],
        }
        for item in display_results
        if item["missing_display_fields"]
    ]
    collections_to_populate = [
        item["name"]
        for item in collections
        if item["classification"] == "Preparada sin datos"
    ]
    collections_to_mark_legacy = [
        item["name"]
        for item in collections
        if item["classification"] in {"Legacy/compatibilidad", "Legacy sin uso"}
    ]

    if incomplete_relations:
        next_step = (
            "Priorizar poblar o reconciliar las dimensiones con faltantes antes de cualquier limpieza lógica, "
            "empezando por la relación con mayor missing_fact_rows."
        )
    elif missing_display_fields:
        next_step = (
            "La integridad de llaves está estable; el siguiente paso recomendable es completar campos display "
            "en dimensiones visibles para endurecer el consumo frontend/reportes."
        )
    else:
        next_step = (
            "El siguiente paso recomendable es definir una política de etiquetado legacy y un plan de población "
            "para colecciones preparadas sin datos, sin eliminar colecciones todavía."
        )

    return {
        "complete_relations": complete_relations,
        "incomplete_relations": incomplete_relations,
        "missing_display_fields": missing_display_fields,
        "collections_to_populate": collections_to_populate,
        "collections_to_mark_legacy": collections_to_mark_legacy,
        "next_step_recommendation": next_step,
    }


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Auditoría del modelo MongoDB GA03")
    lines.append("")
    lines.append(f"- Generado: `{report['generated_at']}`")
    lines.append(f"- Base auditada: `{report['database']}`")
    lines.append(f"- URI objetivo: `{report['mongo_uri']}`")
    lines.append(f"- Modo: `solo lectura`")
    lines.append("")
    lines.append("## Resumen ejecutivo")
    lines.append("")
    lines.append(f"- Colecciones auditadas: **{len(report['collections']['collections'])}**")
    lines.append(f"- Filas en `{FACT_COLLECTION}`: **{report['fact_metrics']['total_rows']:,}**")
    lines.append(f"- Relaciones con cobertura completa: **{len(report['recommendations']['complete_relations'])}**")
    lines.append(f"- Relaciones con faltantes: **{len(report['recommendations']['incomplete_relations'])}**")
    lines.append("")
    lines.append("## Relaciones fact-dim")
    lines.append("")
    lines.append("| Relación | Cobertura filas | Cobertura llaves | Filas faltantes | Llaves faltantes | Estado |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for item in report["relations"]:
        relation_name = f"`{item['fact_field']}` -> `{item['dimension_collection']}.{item['dimension_field']}`"
        row_pct = f"{item['row_coverage_ratio'] * 100:.2f}%"
        key_pct = f"{item['distinct_coverage_ratio'] * 100:.2f}%"
        status = "Completa" if item["is_complete"] else "Con faltantes"
        lines.append(
            f"| {relation_name} | {row_pct} | {key_pct} | {item['missing_fact_rows']:,} | {item['missing_distinct_keys']:,} | {status} |"
        )
    lines.append("")
    lines.append("## Campos display")
    lines.append("")
    lines.append("| Colección | Filas | Display disponible | Display faltante |")
    lines.append("| --- | ---: | --- | --- |")
    for item in report["display_audit"]:
        available = ", ".join(f"`{name}`" for name in item["available_display_fields"]) or "Ninguno"
        missing = ", ".join(f"`{name}`" for name in item["missing_display_fields"]) or "Ninguno"
        lines.append(f"| `{item['collection']}` | {item['total_rows']:,} | {available} | {missing} |")
    lines.append("")
    lines.append("## Métricas de negocio en fact")
    lines.append("")
    fact_metrics = report["fact_metrics"]
    lines.append(f"- `click_bool = true`: **{fact_metrics['click_bool_true']:,}**")
    lines.append(f"- `reserva_bool = true`: **{fact_metrics['reserva_bool_true']:,}**")
    lines.append(f"- `reservas_brutas_usd > 0`: **{fact_metrics['reservas_brutas_usd_positive']:,}**")
    lines.append(f"- `promotion_flag = true`: **{fact_metrics['promotion_flag_true']:,}**")
    lines.append("")
    lines.append("## Clasificación de colecciones")
    lines.append("")
    lines.append("| Colección | Conteo | Clasificación | Referencias código |")
    lines.append("| --- | ---: | --- | ---: |")
    for item in report["collections"]["collections"]:
        lines.append(
            f"| `{item['name']}` | {item['count']:,} | {item['classification']} | {item['reference_count']} |"
        )
    lines.append("")
    lines.append("## Candidatas")
    lines.append("")
    complete_relations = report["recommendations"]["complete_relations"]
    incomplete_relations = report["recommendations"]["incomplete_relations"]
    missing_display_fields = report["recommendations"]["missing_display_fields"]
    lines.append("### Relaciones con cobertura completa")
    lines.append("")
    for item in complete_relations or ["Ninguna."]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("### Relaciones con faltantes")
    lines.append("")
    if incomplete_relations:
        for item in incomplete_relations:
            lines.append(
                f"- {item['relation']}: `{item['missing_fact_rows']}` filas fact sin match y `{item['missing_distinct_keys']}` llaves distintas faltantes."
            )
    else:
        lines.append("- Ninguna.")
    lines.append("")
    lines.append("### Campos display faltantes")
    lines.append("")
    if missing_display_fields:
        for item in missing_display_fields:
            fields = ", ".join(f"`{field}`" for field in item["fields"])
            lines.append(f"- `{item['collection']}`: {fields}")
    else:
        lines.append("- Ninguno.")
    lines.append("")
    lines.append("### Colecciones candidatas a poblar")
    lines.append("")
    for item in report["recommendations"]["collections_to_populate"] or ["Ninguna."]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("### Colecciones candidatas a marcar como legacy")
    lines.append("")
    for item in report["recommendations"]["collections_to_mark_legacy"] or ["Ninguna."]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Recomendación de siguiente paso")
    lines.append("")
    lines.append(f"- {report['recommendations']['next_step_recommendation']}")
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    settings = get_settings()
    db = get_database()
    relation_results = [
        relation_coverage(db, FACT_COLLECTION, fact_field, dim_collection, dim_field)
        for fact_field, dim_collection, dim_field in RELATION_SPECS
    ]
    display_results = [
        display_audit(db, collection_name, fields)
        for collection_name, fields in DISPLAY_SPECS.items()
    ]
    collection_results = build_collection_audit(db)
    recommendations = recommendation_block(
        relation_results,
        display_results,
        collection_results["collections"],
    )
    return {
        "generated_at": utc_now_iso(),
        "database": settings.mongo_database,
        "mongo_uri": settings.mongo_uri,
        "fact_collection": FACT_COLLECTION,
        "relations": relation_results,
        "display_audit": display_results,
        "fact_metrics": build_fact_metrics(db),
        "collections": collection_results,
        "recommendations": recommendations,
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(build_markdown(report), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(
        json.dumps(
            {
                "database": report["database"],
                "collections_audited": len(report["collections"]["collections"]),
                "complete_relations": len(report["recommendations"]["complete_relations"]),
                "incomplete_relations": len(report["recommendations"]["incomplete_relations"]),
                "json_report": str(JSON_REPORT_PATH),
                "markdown_report": str(MARKDOWN_REPORT_PATH),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
