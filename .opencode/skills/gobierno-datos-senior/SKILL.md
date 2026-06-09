---
name: gobierno-datos-senior
description: Use when designing data pipelines, ETL/ELT workflows, data contracts, data quality frameworks, data lineage, Medallion architecture (Bronze/Silver/Gold), data lakehouse, data mesh, data cataloging, or data governance policies. Covers the full data lifecycle from ingestion to consumption.
---

# Senior Data Governance & Architect

## 2026 Landscape
- **Lakehouse** (open formats on object storage + warehouse query) is the dominant storage pattern
- **Data Mesh** (domain-owned data as products) is the dominant organizational model for enterprises
- **Data Fabric** (metadata-driven integration) connects disparate systems without physical movement
- **Data Contracts** are the standard interface between data producers and consumers
- **Medallion Architecture** (Bronze → Silver → Gold) is the standard ETL pattern
- **Open formats**: Parquet, Delta Lake, Iceberg (this project uses CSV → MongoDB which is fine for its scale)

## This Project Data Architecture

### Medallion Architecture (Current)
```
Bronze (Raw)       Silver (Clean)        Gold (Business)
─────────────────  ────────────────────  ─────────────────────
data/raw/          data/processed/        MongoDB collections
hotels.csv         expedia_reservations   dim_hotels
                   _clean.csv             dim_destinations
                                          dim_dates
                                          fact_hotel_reservations
```

### ETL Pipeline Flow (in detail)
```
1. Validate Environment
   │  checks: Python version, MongoDB reachable, CSV exists
   ▼
2. Extract CSV
   │  chunked reads (50K rows), typed columns
   ▼
3. Validate Schema
   │  required columns, data types, no nulls in keys
   ▼
4. Transform Clean
   │  date parsing, int/float coercion, null handling
   ▼
5. Transform Dimensions
   │  dim_hotels, dim_destinations, dim_dates, etc.
   ▼
6. Transform Facts
   │  fact_hotel_reservations with foreign keys
   ▼
7. Quality Report
   │  completeness, uniqueness, range checks
   ▼
8. Load to MongoDB
   │  bulk upserts, ordered=False for speed
   ▼
9. Create Indexes
   │  unique indexes on dimension keys
   ▼
10. Save Execution Report
    │  duration, row counts, error log
```

## Data Quality Framework

### Quality Gates (defined in `src/etl/quality.py`)
| Gate | Check | Severity |
|---|---|---|
| Completeness | No nulls in `date_time`, `prop_id`, `srch_destination_id` | BLOCKING |
| Type safety | Numbers parse, dates parse, booleans coerce | BLOCKING |
| Uniqueness | No duplicate `srch_id` within batch | WARNING |
| Range | Prices > 0, ratings 0-5, dates not in future | WARNING |
| Referential | Foreign keys reference existing dimensions | WARNING |

### Quality Report Format
```json
{
  "dataset": "expedia_reservations_clean.csv",
  "total_rows": 300000,
  "verified_rows": 298500,
  "failed_rows": 1500,
  "failed_details": [
    {"row": 1500, "field": "price_usd", "issue": "negative value", "value": "-10.50"}
  ],
  "gates_passed": 4,
  "gates_failed": 1,
  "timestamp": "2026-06-02T13:30:00Z"
}
```

## Data Contracts

### Collection Schemas (from `src/etl/schema.py`)
Each MongoDB collection has a documented schema:

| Collection | Primary Key | Required Fields | Source |
|---|---|---|---|
| `dim_hotels` | `prop_id` (int, unique) | `prop_id`, `hotel_name` | CSV seed |
| `dim_destinations` | `srch_destination_id` (int, unique) | `srch_destination_id`, `destination_name` | CSV seed |
| `dim_dates` | `date_key` (int, unique) | `date_key`, `full_date`, `year`, `month`, `day`, `hour` | CSV seed |
| `dim_promotions` | `promotion_flag` (0/1) | `promotion_flag`, `promotion_name` | Static seed |
| `dim_reservation_status` | `reserva_bool` (0/1) | `reserva_bool`, `status_name` | Static seed |
| `fact_hotel_reservations` | `source_record_id` | All dimension foreign keys + metrics | ETL load |
| `system_catalogs` | `catalog_type` + `code` | `catalog_type`, `code`, `label` | Seed script |
| `users` | `_id` | `username`, `email`, `password_hash`, `primary_role` | Init script |

### Data Dictionary Standards
- Field names: `snake_case`
- Date fields: ISO 8601 strings
- Monetary values: Decimal / float (not cents as int)
- Booleans: Python `bool` / MongoDB `true/false`
- IDs: `ObjectId` for internal refs, `int` for business keys

## Data Lineage

Every ETL run records:
```
execution_id → [ source_file, row_count, transformations[],
                 target_collection, docs_loaded, errors[],
                 started_at, completed_at, duration_ms ]
```

Stored in `execution_reports` collection. Also available in `data/reports/*.json`.

### Current Execution Tracking
| File | What |
|---|---|
| `data/reports/ga03_full_integrations_report.json` | Full ETL run report |
| `data/reports/ga03_display_dimensions_report.json` | Dimension load report |
| `data/reports/quality/` | Quality gate results |
| `data/staging/ga03_execution_state.json` | Real-time execution state |
| `data/reports/app_server.log` | Application log |

## Governance Policies

### 1. Data Ownership
```
Collection Owner        Steward         Contact
────────── ──────────── ─────────────   ─────────────────────
dim_*       Platform     ETL pipeline   (config in code)
fact_*      Platform     ETL pipeline   (config in code)
users       Auth module  Dev team       admin@hoteldata.local
system_*    Platform     Dev team       admin@hoteldata.local
```

### 2. Retention Policy
| Data | Retention | Action |
|---|---|---|
| Raw CSVs (`data/raw/`) | 90 days | Delete oldest |
| Processed CSVs (`data/processed/`) | 90 days | Delete oldest |
| MongoDB facts | Indefinite | Archive annually |
| Execution reports | 1 year | Compress after 6 months |
| Logs (`*.log`) | 30 days | Rotate + delete |
| Staging files (`data/staging/`) | 7 days | Auto-clean |

### 3. PII / Sensitive Data
- **Current**: No PII in the hotel reservation dataset
- **If PII added**:
  - Encrypt at rest (MongoDB encryption at rest)
  - Mask in logs (don't log raw email, IP, etc.)
  - Field-level access control by role
  - `GDPR` / `CCPA` ready: ability to delete user data

### 4. Data Security
- MongoDB network isolated to Docker compose network
- No direct MongoDB port exposure to host (only other containers)
- PocketBase connected via HTTP API, not direct DB
- Redis password optional, disabled in dev

## Monitoring & Observability

### Data Freshness
```python
# Check most recent loaded_at in fact_hotel_reservations
last_load = db.fact_hotel_reservations.find_one(
    sort=[("loaded_at", -1)],
    projection={"loaded_at": 1, "_id": 0}
)
```

### Data Volume Alerts
- Row count delta > 20% vs historical average → alert
- Execution duration > 2× historical average → alert
- Zero rows loaded (success but empty) → warning

### Health Dashboard
Available via:
- `GET /api/etl-status` → last execution state
- `GET /api/quality` → last quality report
- `GET /api/collections` → collection list + metadata
- `GET /system/redis-status` → cache health

## Data Mesh Concepts (for future growth)
```
Domain Team A (Reservations)      Domain Team B (Revenue)
  Owns: fact_hotel_reservations     Owns: revenue_metrics
  Publishes: reservation data       Publishes: revenue data
  Consumers: dashboard, reports     Consumers: finance, BI
  Data Product:                     Data Product:
    - schema: data contract           - schema: data contract
    - SLA: freshness < 1h             - SLA: freshness < 24h
    - quality: > 99.5%                - quality: > 99%
```

## References
- Medallion Architecture: https://www.databricks.com/glossary/medallion-architecture
- Data Mesh: https://www.datamesh-architecture.com/
- Data Contracts: https://datacontract.com/
- OWASP Data Security: https://owasp.org/www-project-data-security/
