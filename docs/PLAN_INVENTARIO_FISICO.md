# Plan: Inventario Físico con Trazabilidad Económica

> Documento vivo. Se actualiza a medida que avanzamos "paso por paso".
> Items marcados con `☐ DECIDE` requieren tu confirmación antes de implementar.
> Items marcados con `📌 DESPUÉS` quedan como backlog explícito.

## PIVOTE: Plan simplificado (round 3)

El plan original (Opción C con 8 collections nuevas: `inventory_products`, `inventory_suppliers`, `inventory_locations`, `inventory_stock_levels`, `inventory_stock_movements`, `inventory_purchase_orders`, etc.) era sobre-ingenieriado. El usuario señaló correctamente:

> "no me cuadra que haya algo híbrido entre hotel_products y demás tablas, 1 de ellas no debe ser integrada en hotel_products? ya hay mucho hecho veo yo, faltaría poco o lo que vamos a integrar es diferente?"

**Pivote validado** (post thinker + exploración de `expense_invoices`):

1. `hotel_products` ya tiene `quantity_available` + decrement logic en `add_booking_line_item`. Pero **NO tiene costo** ni supplier.
2. `expense_invoices` ya tiene `vendor_name` + `amount` + posting al ledger. Pero **NO tiene line_items**.
3. Conectar los dos es ~20% del esfuerzo original.

**El plan nuevo** (siguiente iteración) usa **las mismas 2 collections existentes** y les agrega 2+ campos:

- `hotel_products`: + `cost_price`, + `type` (retail|supply|asset), + opcional `default_supplier`
- `expense_invoices`: + opcional `line_items: [{product_id, qty, unit_cost}]`
- Cuenta ledger + `5110 - Costo de Amenities Consumidos` para COGS
- Hook al aprobar invoice: +stock + update `cost_price`
- Hook al vender (booking line item): -stock + post COGS DR/CR

Lo que se eliminó del plan: `inventory_products`, `inventory_suppliers`, `inventory_locations`, `inventory_stock_levels`, `inventory_stock_movements`, `inventory_purchase_orders` — todas inecesarias para el tracability economy que el usuario quiere.

---## Cambios en este round

| Sección | Qué cambió | Por qué |
|---|---|---|
| §4 | Tabla comparativa A vs C vs B más detallada | Justificar recomendación |
| §5 | Plan completo simplificado al mínimo delta | Pivote del usuario |
| §6 | Backlog "DESPUÉS" reducido | Gran parte ahora integrado |
| §10 | Reescrito con extensión a `hotel_products` + nota de exclusión de `expense_invoices` | round 6 — esto es lo que se va a hacer |
| §14 | Hallazgo sobre UI faltante en `hotel_products` | round 4 — user preguntó `que hace esa UI si dices q su ruta es esa` |
| §15 | **DUMP anterior**: tenía matrix comparativa artificial `Dual vs Single`. **Reemplazado** por diseño único justificado | round 6b — el usuario dijo "no elegí esos bandos, es confusión tuya" — rectificación |
| §16 | Plan de implementación final consolidado | implementar cuando confirmé abajo |

### Nota sobre la §15 anterior

La §15 original proponia una matrix artificial `Dual vs Single` que el usuario nunca pidió. Se elimina porque:

1. El usuario no estaba eligiendo entre "Dual" y "Single" — solo queria entender por qué dos fuentes.
2. La pregunta real era: ¿cuál es la fuente canónica para inventory traceability?
3. La respuesta no es una opción, es una recomendación basada en investigación del codebase real.

Lo que importa ahora: **una sola fuente** (`hotel_products` extendida). No es un menú dual — es la decisión arquitectónica final.

---



---

## 1. Contexto y motivación

**Problema detectado**: HotelData actualmente no modela el inventario físico de productos que se reponen, consumen o distribuyen en cada habitación. El sistema sabe:

- Qué amenidades se ofrecen al huésped (catálogo comercial)
- Qué precio retail se cobra por ellas
- Qué tareas de housekeeping aplican a un room

…pero **no sabe**:

- Cuánto cuesta al hotel cada producto (`unit_cost`)
- Quién es el proveedor por item (no por factura)
- Cuántas unidades hay realmente en el almacén / en cada habitación
- Cuándo se consumieron y contra qué estancia (Huérfanos de COGS por stay)
- Cuándo hay que reordenar (par levels)

El usuario sospecha el gap y pregunta si es "feature grande". Lo es, pero acotado: no necesitamos un ERP completo (como **Oracle Materials Control**) sino un MVP híbrido que cierre la trazabilidad básica con la granularidad que ya existe en el resto del sistema.

**Beneficio esperado**:

- Trazabilidad real de producto (compra → almacen → consumo → estancia → COGS)
- Reporte de margen por amenidad (precio retail - costo = utilidad)
- Alertas de reorder automáticas (par levels)
- Auditoría física (ciclos de count, ajustes)

---

## 2. Estado actual del codebase

### 2.1 Lo que YA existe (y por qué NO cubre esto)

| Colección / Función | Path | Qué cubre | Por qué no es inventario físico |
|---|---|---|---|
| `hotel_content_pages.amenity_prices` | `partner/services/content/amenities.py` | Precio **RETAIL** cargado al huésped | Precio de venta, no costo |
| `_amenity_unit_price(label)` | `partner/services/content/amenities.py:104` | Default retail por nombre | Mismo problema — retail only |
| `hotel_products` | sembrado por `scripts/seed_hotel_products.py` | Catálogo retail (Minibar $3.50, Spa Masaje $60) | Tiene `unit_price` (venta) y `quantity_available=50` aleatorio, **PERO** ver §2.3 — ya tiene un esqueleto de stock |
| `expense_invoices.vendor_name` | `modules/expenses/schemas.py:31` | Proveedor por **factura** completa | Necesitamos proveedor por **item**, no por factura |
| `housekeeping_tasks` | `modules/housekeeping/` | Tareas (limpiar baño, reponer amenities) | Tareas narrativas — no mueven stock ni linkean a un producto físico |
| `housekeeping_charges` | `modules/housekeeping/` | Cargo al huésped por servicio consumido | Registra venta, no descuenta inventario |
| `chart_of_accounts` cuenta `1050` "Inventario de amenities" | `scripts/seed_chart_of_accounts.py:16` | Definida como `asset debit` | Pero **nadie** postea movimientos contra esa cuenta — está huérfana (ver §2.4) |
| `room_inventory_calendar` | `modules/partner/services/inventory*.py` | Inventario de HABITACIONES (availability por fecha) | Es disponibilidad de rooms PARA VENTA, no productos físicos en cada room |
| `additional_charges` | `modules/billing/` | Cargo al huésped por consumption | Origen comercial, no descuenta inventario |

### 2.3 El esqueleto medio ya existente en `hotel_products`

Investigación detallada (ver §2.5 - call graph) encontró que `hotel_products` ya tiene tracking rudimentario:

```python
# partner/services/hotel_products.py:179 (add_booking_line_item)
if qty_avail >= quantity:
    db.hotel_products.update_one(
        {"product_id": product_id},
        {"$inc": {"quantity_available": -quantity}},   # ← decrementa al vender
    )

# partner/services/hotel_products.py:287 (remove_booking_line_item)
db.hotel_products.update_one(
    {"product_id": pid, "quantity_available": {"$gt": 0}},
    {"$inc": {"quantity_available": qty}},            # ← restaura al remover
)
```

**Lo que FALTA en ese esqueleto**:
- Distribucción por ubicación (solo `quantity_available` agregado)
- `unit_cost` (solo `unit_price` retail)
- `unit_cost` histórico (no `unit_cost_at_time` para los movements)
- Proveedor (no `default_supplier_id`)
- Log de movimientos (no `stock_movements` collection)
- Par levels / reorder point
- Multi-location splits (todo es un solo contador)

**Conclusión**: NO reemplazar `hotel_products`. La decisión es Opción 0c (coexisten).

### 2.4 Estado de `chart_of_accounts` 1050

| Campo | Valor |
|---|---|
| `account_code` | `1050` |
| `account_name` | `Inventario` |
| `account_type` | `asset` |
| `normal_balance` | `debit` |
| `parent_code` | `1000` (Activos) |
| `level` | 2 |
| `description` | `"Inventario de amenities, suministros, alimentos"` |

**Movimientos contra 1050**: confirmado con grep — **CERO**. Solo el seed la define.

**Propuesta para Fase 7**:
- Mantener `1050 - Inventario de amenities, suministros, alimentos`
- Crear nueva cuenta `5110 - Costo de Amenities Consumidos` (expense, debit, parent `5000`)
- Wiring al consume → DR `5110` + CR `1050` = balance neto cero

### 2.5 Call graph de `hotel_products`

```
Callers activos (todos los que conectan):
├── server/scripts/seed_hotel_products.py            (seed)
├── server/scripts/cleanup_demo_data.py:43           (clean seed)
├── server/scripts/migrate_fk_hotel_id.py:56         (backfill hotel_id)
├── server/src/app/main.py:96                        (router register)
├── server/src/app/modules/billing/lifecycle/invoices.py:46
│     (record_platform_earnings al crear invoice)
├── server/src/app/modules/partner/routes/hotel_products.py (CRUD + line_items + earnings)
├── server/src/app/modules/partner/services/bootstrap.py:129
│     (index bootstrap bajo "ROOM_FEATURES_COLLECTIONS" — mal nombrado)
└── server/src/app/modules/partner/services/hotel_products.py (CRUD + add/remove line items)
```

NO hay documentación previa (`/docs/*.md`) que documente este intento medio-abandonado. Fue implementación directa sin spec.

### 2.2 El gap explícito

| Dimensión | Estado |
|---|---|
| Item-level cost (`unit_cost`) | NO existe |
| SKU por item (barcode del proveedor) | NO existe |
| Proveedor POR ITEM (FK, no string en factura) | NO existe |
| Locations jerárquicas (almacén → piso → habitación) | NO existe |
| Stock físico `on_hand` por ubicación | NO existe |
| Par levels / reorder points | NO existe |
| Stock movements (in / out / transfer / consume / adjust / audit) | NO existe |
| Distribución item→room (1 caja shampoo = 32 frascos → 8 rooms × 4) | NO existe |
| Trazabilidad por unidad (lote, fecha caducidad, QR/UDI) | NO existe |
| COGS por estancia (costo de amenities consumidos) | NO existe |
| Purchase orders linkeadas a `expense_invoices` | NO existe |
| Reporte de valor de inventario / alertas de reorder | NO existe |
| Ledger_hook que postee contra cuenta `1050` | NO existe |

---

## 3. Cómo lo manejan los PMS grandes (research)

- **99% de los PMS NO manejan esto nativamente** — es un sub-módulo o integración externa.
- **Oracle OPERA**: usa **Oracle Hospitality Materials Control** (módulo separado) para costos, proveedores, par levels, P&L. La integración es profunda pero opaca — pocas propiedades lo activan.
- **Mews / Cloudbeds**: solo productos básicos en POS / Housekeeping; procurement complejo via API con apps third-party (AppStore).
- **Hotelkit**: maneja la capa de tarea (housekeeping registra consumo), pero la parte financiera la hace integración externa.
- **Patrón consistente en la industria**:
  - **Reception** → solo ve *charges* (billing al huésped)
  - **Housekeeping** → solo ve *tasks* (qué se consumió / qué reponer)
  - **Purchasing / Back-office** → control exclusivo de *costs + vendors + reorder + P&L*

### 3.1 Tabla comparativa de capacidades

| Función | Reception | Housekeeping | Purchasing | Manager |
|---|---|---|---|---|
| Consumption tracking | view (billing) | primary input | data analysis | full |
| Par levels / stock | visibility of "in-stock" | workflow trigger | management / setting | full |
| Vendor / costing | none | none | primary control | full |
| P&L reporting | guest-ledger focus | consumption log | COGS / financials | full |

---

## 4. Decisión de arquitectura (A / B / C)

| Dimensión | **A — Nativo completo tipo OPERA** | **C — Híbrido liviano MongoDB (RECOMENDADO)** |
|---|---|---|
| Complejidad | ERP-grade: Materials Control con sync bidireccional al ledger | 6 collections lightweight en MongoDB |
| Reorder automation | ✅ automática (par levels → PO auto) | ❌ manual (gerente off-line) |
| Ciclos de auditoría física | ✅ recuentos ciegos + variance analysis | ❌ manual via `stock_movement(type=adjust)` |
| Trazabilidad por unidad (lote, UDI) | ✅ cada frasco / UDI único | ❌ agregados solamente |
| Multi-property consolidation | ✅ roll-up consolidado | ❌ per-property únicamente |
| Integración SAP/QuickBooks | ✅ nativa | ❌ futura (manual) |
| Timeline | 6-9 sprints | 2-3 sprints |
| Mantenimiento | Alto — necesita payroll dedicado | Bajo — mismo ritmo de HotelData |
| Cobertura | 100% enterprise | 80% hoteles medianos |

| Opción | Alcance | Tiempo | Tradeoff |
|---|---|---|---|
| **A — Nativo completo tipo OPERA** | Inventory + Materials Control | 6-9 sprints | Sobre-ingeniería para hotel mediano |
| **B — Integración externa SaaS** | Sortly / Cheqroom + webhook | 1-2 sprints | Costo mensual + doble fuente de verdad |
| **C — Híbrido liviano (RECOMENDADO)** | Collections MongoDB + CRUD + COGS | 2-3 sprints | Todo nativo, sin ERP, 80% casos cubiertos |

### 4.1 DECISIÓN ARQUITECTÓNICA (consolidada en §15)

Opción A/B/C (crear collections nuevas) fue descartada en round 3. La decisión arquitectónica final está consolidada en **§15 — Arquitectura final — una sola fuente**:

- `hotel_products` se extiende con campos de trazabilidad económica (cost_price, supplier, par_level, restock history, soft-delete)
- `expense_invoices` queda intacta (sigue registrando gastos operativos generales del hotel: electricidad, payroll, marketing, servicios)
- Sin menú de bandos. Sin "Opción DUAL". La implementación concreta está en **§16**.

Las secciones §5-§14 contienen material de referencia histórica de rounds previos; **no son la fuente de verdad** para implementar. Implementación = §15 + §16.

---

## 15. Arquitectura final — una sola fuente

Esto es lo que se hace. No hay menú de bandos.

Tras auditar cómo operan los módulos reales, la decisión es centralizar la gestión de inventario en una única fuente de verdad extendiendo lo que ya existe y funciona.

### 15.1 Hallazgos clave del código

1. **`hotel_products` es el motor natural**: Ya funciona como catálogo comercial, tiene los campos base (`quantity_available`, `unit_price`), tiene lógica de decremento de stock en `add_booking_line_item` y afecta a 8 archivos clave. Solo le falta interfaz gráfica (UI) y el concepto de "costo".
2. **`expense_invoices` tiene otro propósito**: Está estructurado para registrar "gastos/facturas" de proveedores por factura completa (electricidad, marketing, servicios), sin la estructura ni la necesidad nativa de manejar *line items* individuales de inventario. Para el demo (Hotel Lima Centro) todas las facturas son de servicios (energía, agua, payroll).
3. **Ledger preparado pero dormido**: La cuenta contable `1050 (Inventario)` ya existe sembrada en el sistema, lista para recibir asientos automatizados, pero actualmente ningún módulo le envía movimientos.

### 15.2 La Arquitectura

El inventario físico vivirá estrictamente extendiendo `hotel_products`. La colección `expense_invoices` se quedará como está.

**Cómo funciona el flujo:**

- **Asentar la compra:** El hotel recibe una factura de proveedor por $200 de amenidades y la carga como un gasto normal en `expense_invoices` (vendor + amount + category + date — sin cambiar schema).
- **Reponer el físico:** El gerente va a la nueva UI de **Productos**, selecciona el "Shampoo" y hace un *Restock* indicando que entraron 50 unidades a un costo de $1.50 c/u (referenciando opcionalmente el # de factura).
- **Contabilidad automática:** Ese *restock* actualiza la tabla producto y lanza un asiento al Ledger (DR 1050 Inventario).
- **Venta/Consumo:** Cuando el recepcionista o housekeeping añade el item a la reserva, baja el stock y se registra el costo de mercancía vendida (COGS - DR 5110).

### 15.3 Trade-offs y justificación

* **Menor riesgo de inconsistencia:** Al no tratar de sincronizar bidireccionalmente facturas con inventarios, evitamos bloqueos y asimetrías de datos. Un sólo flujo de mutación: `hotel_products.update + ledger post` en una sola operación.
* **Velocidad de entrega:** Representa ~20% del esfuerzo frente a crear todo un módulo de Órdenes de Compra. Un sprint completo en lugar de 2-3.
* **Auditoría suficiente:** El `audit_log` (ya wrapeado por outbox en este codebase) retiene cada cambio de `cost_price`/`quantity_available` con `diff: { old, new }`. Reconstrucción histórica posible vía `entity_type=hotel_product_stock`.
* **Decisión sobre dudas futuras:** Si el hotel crece y exige que las facturas contengan ítems detallados, en el futuro se puede construir un "parser" opcional (`/expense_invoices/{id}/parse_to_restock`) que lea `description` o `notes` con regex y dispare `/restock` automáticamente. **Por ahora, es innecesario**.
* **Cobertura:** Cubre el gap exact que mencionaste: cuánto cuesta cada producto, quién lo proveyó, cuánto queda en stock, COGS por venta, automatización COGS al ledger.

### 15.4 Lo que explícitamente NO se hace

| Decisión | Por qué |
|---|---|
| **No** extender `expense_invoices` con `line_items` | Hoy es bills generales. No tiene estructura nativa ni necesidad de items. |
| **No** crear collection `inventory_*` separada | Sobre-ingeniería. `hotel_products` ya tiene todo lo necesario. |
| **No** modelo "purchase_orders" separado | Compra es un restock directo contra `hotel_products` con ref opcional al invoice. |
| **No** sync atómico MongoDB multi-collection | No hay multi-collection que sincronizar. SINGLE flow. |
| **No** UI page en `/admin/products` | Semánticamente la página de productos NO ES admin (crear productos no es platform admin). Va en módulo aparte `features/products/`. |

### 15.5 El "coupling opcional" entre expense_invoices y hotel_products (futuro)

Si en el futuro llega una factura con items parseables (ej. `notes = "10× shampoo, 5× gel, supplier Coca Cola"`), un trigger opcional puede interpretar notas y llamar `/products/{id}/restock` por cada item detectado.

Ese trigger es:
- Código: ~50 lineas en un trigger_function
- Trigger keys: regex contra `notes` o `description`
- Failure mode: si no parsea, NO bloquea el invoice. Hotel carga factura normalmente sin restock.

**Por ahora en MVP: NO se construye ese trigger.** El gerente hace restock manual desde `/management/products`.

---

## 16. Plan de implementación (lo que se arranca)

**Cuando confirmes abajo, ejecuto este plan en orden.** Sin menu, sin opciones.

### 16.1 Schema extension de `hotel_products`

Campos nuevos: `cost_price`, `type`, `default_supplier`, `supplier_sku`, `par_level`,
`last_purchase_invoice_ref`, `last_purchase_at`, `last_purchase_qty`,
`archived_at`, `archived_by`.

#### Script de migración

```python
# server/scripts/migrate_add_inventory_fields.py
"""Backfill type=retail, cost_price=0, archived_at=None in hotel_products."""
db = get_database()
result = db.hotel_products.update_many(
    {
        "type": {"$exists": False},
    },
    {
        "$set": {
            "type": "retail",
            "cost_price": 0.0,
            "default_supplier": None,
            "supplier_sku": None,
            "par_level": None,
            "last_purchase_invoice_ref": None,
            "last_purchase_at": None,
            "last_purchase_qty": None,
            "archived_at": None,
            "archived_by": None,
            "updated_by": None,
        },
    },
)
print(f"Backfilled {result.modified_count} hotel_products documents.")
```

#### Schema visible

```python
{
  "_id": ObjectId,
  "prop_id": int,
  "hotel_id": ObjectId,                   # FK dim_hotels._id
  "product_id": "PROD-XXXXX",            # human-readable, ya existe
  "name": str,
  "description": str,
  "category": str,                        # "Minibar", "Spa", etc.
  # ─── NUEVOS ──────────────────────────────
  "type": "retail" | "supply" | "asset",  # discriminador (default "retail")
  "cost_price": float,                    # último purchase price
  "default_supplier": str | None,
  "supplier_sku": str | None,
  "par_level": float | None,
  "last_purchase_invoice_ref": str | None,
  "last_purchase_at": datetime | None,
  "last_purchase_qty": float | None,
  # ─── EXISTENTES ──────────────────────────
  "unit_price": float,                    # retail price
  "quantity_available": float,
  "is_active": bool,
  # ─── SOFT DELETE ──────────────────────────
  "archived_at": datetime | None,
  "archived_by": str | None,
  # ─── AUDIT ──────────────────────────────
  "created_by": str,
  "created_at": datetime,
  "updated_at": datetime,
  "updated_by": str | None,
}
```

### 16.2 Nueva cuenta ledger

| Code | Name | Type | Side | Parent |
|---|---|---|---|---|
| `5110` | Costo de Amenities Consumidos | `expense` | `debit` | `5000` |

Agregada a `seed_chart_of_accounts.py`. Ya existe `1050 (Inventario)` que se queda y se le postea.

### 16.3 Nuevos permisos

```python
# En PERMISSION_CATALOG en init_security_model_ga03.py
("inventory.products.cost.read",   "Ver costo unitario (manager-only)"),
("inventory.products.cost.manage", "Editar costo unitario (manager-only)"),
```

Asignados a `gerente_hotel` (todos), NO a `recepcionista` (no ven cost).

### 16.4 Nuevo endpoint REST `/restock`

```python
# server/src/app/modules/partner/routes/hotel_products.py (extension)

@router.post("/products/hotels/{prop_id}/{product_id}/restock")
def restock_product(
    prop_id: int,
    product_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("inventory.products.cost.manage")),
):
    """Registra reposición manual sin invoice formal. Actualiza stock + cost_price."""
    db = get_database()
    product = db.hotel_products.find_one({"product_id": product_id, "prop_id": prop_id})
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    qty = float(payload.get("qty", 0))
    unit_cost = float(payload.get("unit_cost", 0))
    supplier = payload.get("supplier_name", "") or product.get("default_supplier", "")
    invoice_ref = payload.get("invoice_ref", "") or None

    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty debe ser > 0")
    if unit_cost < 0:
        raise HTTPException(status_code=400, detail="unit_cost debe ser >= 0")

    old_cost = product.get("cost_price", 0.0)
    update_doc = {
        "quantity_available": product.get("quantity_available", 0) + qty,
        "cost_price": unit_cost,                              # update (or moving-average in futuro)
        "default_supplier": supplier,
        "last_purchase_invoice_ref": invoice_ref,
        "last_purchase_at": datetime.now(timezone.utc),
        "last_purchase_qty": qty,
        "updated_at": datetime.now(timezone.utc),
        "updated_by": current_user.get("username", "system"),
    }
    db.hotel_products.update_one({"product_id": product_id, "prop_id": prop_id}, {"$set": update_doc})

    # Ledger DR 1050 / CR 2010 (Ctas por Pagar Proveedores)
    # post_journal_entry se AGREGARÁ en Fase 3 al ledger_hooks.py (wrapper sobre _insert_entry + _journal_seq).
    # NO existe aún en el codebase — se define como parte de este feature.
    from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
    post_journal_entry(
        amount=round(qty * unit_cost, 2),
        dr_account_code="1050",  # Inventario
        dr_account_name="Inventario",
        cr_account_code="2010",  # Cuentas por Pagar Proveedores
        cr_account_name="Cuentas por Pagar Proveedores",
        description=f"Restock {product_id}: {qty} unidades @ {unit_cost} (supplier {supplier})",
        prop_id=prop_id,
        source="hotel_product_restock",
        source_id=invoice_ref or "manual",
    )

    # Audit row via outbox
    register_action(
        prop_id=prop_id,
        entity_type="hotel_product_stock",
        entity_id=f"in:{product_id}",
        action="restock",
        summary=f"Reponen {qty} unidades de {product_id} @ {unit_cost} (supplier {supplier})",
        changed_by=current_user.get("username", "system"),
        diff={
            "qty_added": qty,
            "cost_price": {"old": old_cost, "new": unit_cost},
            "supplier": supplier,
            "invoice_ref": invoice_ref,
        },
    )
    return {**update_doc, "product_id": product_id, "prop_id": prop_id}
```

### 16.5 Hook en `add_booking_line_item` + ledger COGS

```python
# En server/src/app/modules/partner/services/hotel_products.py (extension)
# justo al final de add_booking_line_item, despues del $inc de quantity_available -quantity:

if total > 0:
    unit_cost = product.get("cost_price", 0)
    if unit_cost > 0:
        cogs = round(unit_cost * quantity, 2)
        post_journal_entry(
            amount=cogs,
            dr_account_code="5110",  # Costo de Amenities Consumidos
            dr_account_name="Costo de Amenities Consumidos",
            cr_account_code="1050",  # Inventario
            cr_account_name="Inventario",
            description=f"COGS por venta de {safe_name} (qty {quantity}) en booking {booking_id}",
            prop_id=booking["prop_id"],
            source="booking_line_item_sale",
            source_id=item_id,
            booking_id=booking_id,
        )
```

### 16.6 Hook en `remove_booking_line_item` (reversal)

```python
# En server/src/app/modules/partner/services/hotel_products.py (extension)
# al final de remove_booking_line_item, despues de restaurar quantity_available:

if item_total > 0 and item and pid:
    product = db.hotel_products.find_one({"product_id": pid}, {"cost_price": 1})
    if product and product.get("cost_price", 0) > 0:
        cogs_reversal = round(product["cost_price"] * item.get("quantity", 1), 2)
        # Reversal: invert debit/credit of the original posting (DR 1050 / CR 5110).
        post_journal_entry(
            amount=cogs_reversal,
            dr_account_code="1050",  # Inventario (re-entra)
            dr_account_name="Inventario",
            cr_account_code="5110",  # Costo de Amenities (se reversa)
            cr_account_name="Costo de Amenities Consumidos",
            description=f"COGS REVERSAL {item_id} (qty {item.get('quantity', 1)})",
            prop_id=item.get("prop_id"),
            source="booking_line_item_reversal",
            source_id=item_id,
            booking_id=item.get("booking_id", ""),
        )
```

### 16.7 UI nueva `/management/products`

#### List page (`products-list-page.html`)
- Toolbar arriba:
  - Search box por name
  - Filtros chip por `type`: "Todos" / "Retail" / "Supply" / "Activos"
  - Filter por `is_active` (default active only)
  - Botón "+ Nuevo producto" (manager only)
- Tabla:
  | Product ID | Name | Category | Type | Costo | Retail | Margen | Stock | Status |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | (link to edit) | | | | (manager only) | | =retail-cost (manager only) | | |
- Botones por fila:
  - Ver detalle (read)
  - Editar (manager)
  - Reponer stock (manager) → abre modal

#### Form page (`products-form-page.html`)
- Inputs:
  - `name` (req)
  - `description` (textarea)
  - `category` (select con categorías + option "Other")
  - `type` (select retail/supply/asset, default retail)
  - `cost_price` (number, manager only)
  - `unit_price` (number, retail)
  - `default_supplier` (text, optional)
  - `supplier_sku` (text, optional)
  - `par_level` (number, optional)
  - `quantity_available` (READONLY display)
  - `is_active` (toggle)
- Validations:
  - `cost_price >= 0`, `unit_price >= 0`, `quantity_available >= 0`
  - `name min(2)`, `category required`
- Errors inline with @if
- On submit: POST / PUT al backend service

#### Restock modal
- Inputs: `qty`, `unit_cost`, `supplier_name` (auto-fill default supplier), `invoice_ref` (optional text)
- Validation: qty > 0, unit_cost >= 0
- Submit: POST `/products/hotels/{prod_id}/restock`
- Después cierra modal + refresh list

### 16.8 Sidebar-nav entry

```python
# init_security_model_ga03.py, NAVIGATION_CATALOG
{"label": "Productos", "href": "/management/products", "icon": "inventory_2", "required_permission": "properties.read", "section": "PMS", "sort_order": 209}
```

### 16.9 Reportes nuevos

| Reporte | Endpoint | Permiso |
|---|---|---|
| Margin analysis | `/api/management/products/reports/margin?prop_id=N` | `inventory.products.cost.read` |
| COGS por período | `/api/management/products/reports/cogs?prop_id=N&from=...&to=...` | `inventory.products.cost.read` |
| Stock value | `/api/management/products/reports/value?prop_id=N` | `inventory.products.cost.read` |
| Restock history | `/api/management/products/{id}/restock-history?prop_id=N` | `inventory.products.cost.read` |

Minimo MVP = `stock_value` + `margin` (2 reportes). `cogs` y `restock_history` quedan en DESPUÉS.

### 16.10 Orden de ejecución

1. **Fase 1 ~3-5 días**: Schema + backfill migration + extender seed_hotel_products.py con cost_price + type
2. **Fase 2 ~1 día**: Permissions + cuenta ledger
3. **Fase 3 ~2-3 días**: Restock endpoint + ledger posting + audit hook
4. **Fase 4 ~2-3 días**: Hook add_booking_line_item + reversal
5. **Fase 5 ~4-5 días**: UI /management/products (3 components: list, form, restock modal)
6. **Fase 6 ~2-3 días**: Reportes (stock value + margin)
7. **Fase 7 ~1 día**: Sidebar-nav entry + smoke tests

**Total: ~16 días (1 sprint)** — factible si arrancamos ya.

**Última cosa**: para arrancar necesito 0 cosa de ti. El código está claro. Si querés un solo cambio del scope (ej. moving-average en lugar de last-purchase-price, o NO UI, o NO reportes), decímelo; si no, voy.



---

## 5. Plan de implementación paso a paso (asumiendo Opción C)

> ⚠️ **OBSOLETE — ver §15.** Esta sección es referencia histórica de rondas previas (asume "Opción C" con 8 collections nuevas: `inventory_products`, `inventory_suppliers`, `inventory_locations`, `inventory_stock_levels`, `inventory_stock_movements`, `inventory_purchase_orders`, etc.). **NO es la fuente de verdad.** La arquitectura final está consolidada en **§15 — Arquitectura final — una sola fuente** y la implementación concreta en **§16**.

### Fase 0 — Decisiones de diseño (estado al cierre de esta conversación)

Investigación detallada en §2 (estado actual) + §10 (lo que necesito de ti):

- ☑ **DECIDIDO**: locations JERÁRQUICO (`parent_id` + `path`). User: "EXCELENTE"
- ✓ **RECOMENDACIÓN (Opción 0c confirmada)**: `hotel_products` RETAIL coexiste con `inventory_products` FÍSICO.
  - `hotel_products` mantiene su rol retail (`unit_price` + `quantity_available` enteros como cache)
  - `inventory_products` es el catálogo físico con `unit_cost`, `default_supplier_id`, par_levels
  - Field opcional `inventory_product_id` en `hotel_products` los vincula
  - `add_booking_line_item` decrementa ambos: `quantity_available` (cache) + crea `inventory_stock_movement(type=consume)` (real)

- ✓ **RECOMENDACIÓN cuenta 1050**: MANTENERLA + empezar a postearle. Crear nueva `5110 - Costo de Amenities Consumidos` para contrapartida.

- ✓ **RECOMENDACIÓN locations**: jerárquico con `parent_id` + `path` array + `kind` (warehouse | floor | room | minibar).

- ✓ **PATRÓN `prop_id` + ObjectId CONFIRMADO**: cada documento lleva:
  - `_id`: ObjectId (MongoDB)
  - `prop_id`: int scalar (scope por propiedad)
  - `hotel_id`: ObjectId FK (resolve_hotel_id(prop_id))
  - `product_id`/`supplier_id`/etc: string semántico (tickets)
  - Ver §10.4 para la definición canónica.

- ✓ **RECOMENDACIÓN soft delete**: `is_active=False` + `archived_at: datetime` + `archived_by: str`.
  - Estándar moderno compatible con el patrón `is_active` (192 archivos ya lo usan) + audit trail explícito (housekeeping tasks + sessions también lo usan).

- ☐ **DECIDE (sin confirmar aún)**: ¿Procedemos con la **Opción C** completa o quieres revisar otros trade-offs antes?
- ☐ **DECIDE**: ¿`product_id` formato `PROD-YYYYMMDD-NNNN-XXXX` o más simple? (ver §10.6)

### Fase 1 — Catalog foundation (`products` + `suppliers`)

**Backend**:

- ☐ Crear `inventory_products` collection (si Opción 0c) o extender `hotel_products` (si 0b)
- ☐ Crear `indexes` con unique constraint en `(prop_id, sku)` y `(prop_id, name)`
- ☐ Crear `inventory_suppliers` collection
- ☐ Endpoints CRUD básicos:
  - `GET /api/management/inventory/products?prop_id=N&category=...&is_active=true`
  - `POST /api/management/inventory/products`
  - `PUT /api/management/inventory/products/{product_id}`
  - `DELETE /api/management/inventory/products/{product_id}` (soft)
  - `GET /api/management/inventory/suppliers` + CRUD equivalente (5 endpoints)
- ☐ Schemas Pydantic v2 con validación (`unit_cost >= 0`, `unit_retail_price >= 0`, `currency in catalog`)
- ☐ Mappers frontend (DTO → model → DTO)

**Frontend**:

- ☐ Página `/management/inventory/products` con grilla, filtros, modal de edición
- ☐ Página `/management/inventory/suppliers` con grilla y modal
- ☐ Wire-up con `httpResource()` (Angular 22 — ya usado en todo el proyecto)
- ☐ `ChangeDetectionStrategy.OnPush` mandatory
- ☐ Navegación: agregar entrada `"Inventario"` con sub-entrías al `NAVIGATION_CATALOG` en `init_security_model_ga03.py`

### Fase 2 — Stock model (`locations` + `stock_levels` + `movements`)

**Backend**:

- ☐ Crear `inventory_locations` collection jerárquica (parent_id, path)
- ☐ Crear `inventory_stock_levels` (one-per-(location, product), unique index)
- ☐ Crear `inventory_stock_movements` con auditoría inmutable (no updates, solo inserts)
- ☐ Endpoints:
  - `GET /api/management/inventory/locations?prop_id=N` (devuelve árbol)
  - `POST /api/management/inventory/locations` (con `parent_id`)
  - `PUT /api/management/inventory/locations/{location_id}` (rename / move parent)
  - `GET /api/management/inventory/stock?prop_id=N&location_id=...&product_id=...&low_stock=true`
  - `POST /api/management/inventory/stock/movements` (tipo: in / out / transfer / adjust / audit)
  - `GET /api/management/inventory/stock/movements?product_id=...&from_date=...&to_date=...`
- ☐ Función helper `_atomic_movement_and_apply()` que dentro de una tx Mongo hace:
  1. insert en `inventory_stock_movements`
  2. update en `inventory_stock_levels.on_hand` (suma o resta según tipo)

**Frontend**:

- ☐ Página `/management/inventory/stock` con vista por ubicación + alertas reorder
- ☐ Página `/management/inventory/movements` con log con filtros
- ☐ Modal "Registrar movimiento" (form: tipo, producto, qty, from/to location, notes)

### Fase 3 — Permissions + roles

**Backend - security**:

- ☐ Agregar códigos al `PERMISSION_CATALOG` en `init_security_model_ga03.py`:
  - `inventory.products.read`
  - `inventory.products.manage`
  - `inventory.stock.read`
  - `inventory.stock.manage`
  - `inventory.suppliers.manage`
  - `inventory.po.manage`
  - `inventory.consume` (para housekeeping app)
- ☐ Asignar permisos a roles:
  - `gerente_hotel`: todas las inventory.*
  - `recepcionista`: `inventory.stock.read`, `inventory.products.read`
  - `housekeeping`: `inventory.stock.read`, `inventory.consume`
  - `operador_datos`: `inventory.products.read`, `inventory.stock.read`
- ☐ Crear rol opcional `inventory_clerk` para el puesto de compras (o reusar `gerente_hotel`)

**Frontend**:

- ☐ Actualizar `evaluation_permissions_chip_can()` para que use `httpResource` correctamente
- ☐ Sidebar-nav filtra las nuevas entradas ("Inventario y Stock", "Proveedores") según permisos

### Fase 4 — UI polish + dashboard

**Frontend**:

- ☐ Dashboard `/management/inventory/dashboard` con KPIs:
  - Valor total de inventario (cost basis)
  - Items bajo reorder point (alerta)
  - Items sin movimiento hace X días (alerta slow-moving)
  - COGS del mes (acumulado de `additional_charges` con `unit_cost` mapeado)
  - Top 10 productos por consumo
- ☐ Grillas con `ag-grid` (ya usado en otras páginas) o patrón nativo Angular 22

### Fase 5 — Wiring con Housekeeping consume

**Backend**:

- ☐ Crear endpoint `POST /api/instay/staff/housekeeping/{task_id}/consume` que:
  1. recibe `[{product_id, qty}]` array
  2. para cada item, inserta `inventory_stock_movements(type=consume, ref=housekeeping_task)`
  3. decrementa `inventory_stock_levels.on_hand` por location (room del task) + ubicación anterior (warehouse)
  4. crea `housekeeping_charges` con `unit_cost` (para COGS) + `unit_retail_price` (si aplica cargar al huésped)
- ☐ Audit row via `register_action()` (best-effort, ya wrapeado por outbox en este código)

**Frontend**:

- ☐ Modal en task de housekeeping: "¿Items consumidos en esta limpieza?" [Sí / No]
- ☐ Si sí, mini-grilla para seleccionar productos + qty
- ☐ Si el item también es vendible al huésped (minibar), opcional escalar a `additional_charges`

### Fase 6 — Purchase orders + integración con `expense_invoices`

**Backend**:

- ☐ Crear `inventory_purchase_orders` collection (header) + `inventory_purchase_order_lines` (o `lines` embebido)
- ☐ Endpoints CRUD PO (7 endpoints — create, list, detail, update, send, receive, cancel)
- ☐ Al `receive` PO: bulk `inventory_stock_movements(type=in, to_location=warehouse)` con `unit_cost=line.unit_cost`
- ☐ Linking con `expense_invoices`: campo opcional `linked_po_id` en invoice; al registrar invoice con `linked_po_id`, validación cruzada

**Frontend**:

- ☐ Página `/management/inventory/purchase-orders` (list + detail + receive modal)
- ☐ Paso 6 marcar completamente como opcional (DESPUÉS si querés)

### Fase 7 — COGS integration (ledger_hook + folio)

**Backend**:

- ☐ `expenses/service/ledger_hooks.py`: agregar handler `inventory_consumption` que postea:
  - DR `5110 - Costo de amenities consumidos` (cuenta nueva)
  - CR `1050 - Inventario de amenities` (cuenta existente)
- ☐ `guest_folios`: agregar campo `cogs_amount` por línea (secalcula en consume)
- ☐ Reporte `/management/reports/cogs` agrupado por producto/categoría/mes

### Fase 8 — ETL seeds (demo data)

- ☐ Crear `scripts/seed_inventory_demo.py` que pobla:
  - ~30 productos demo (shampoo, toalla, minibar items, amenities fijos) con `unit_cost` + `unit_retail_price`
  - ~5 proveedores demo
  - Locations jerárquicas (1 almacén central + 1 piso demo + 1 habitación demo)
  - Stock levels iniciales (~10 unidades por product en almacén)
  - ~5 movimientos demo (entrada inicial, distribución a rooms)
- ☐ Documentar en `docs/MIGRATION_PLAN.md` los pasos de bootstrap

---

## 6. Lo que va DESPUÉS (backlog explícito — pivotado)

> ⚠️ **OBSOLETE — ver §15 + §6.DESPUÉS dentro del doc activo.** Esta sección es referencia histórica del pivote (lista de items DESPUÉS según el plan pre-pivote). Gran parte de estos items han sido **integrados al MVP** o **descartados** en la arquitectura final. La lista vigente de DESPUÉS en el contexto de la nueva arquitectura vive cerca de §15. **NO es la fuente de verdad** para el backlog.

Después del pivote, lo que NO entra en el MVP (gran parte ahora integrado):

📌 **DESPUÉS 1**: Trazabilidad por unidad individual (lote, fecha caducidad, QR/UDI scan-on-consume por frasco). Con el plan actual: agregados solamente.

📌 **DESPUÉS 2**: `inventory_suppliers` FK collection. Por ahora: `expense_invoices.vendor_name` es string. Convertir a FK collection cuando haya >50 proveedores.

📌 **DESPUÉS 3**: `inventory_locations` jerárquico (warehouse costero, mini-bar en cada habitación). Por ahora: `quantity_available` es agregado del hotel.

📌 **DESPUÉS 4**: `inventory_stock_movements` audit log completo con transferring + adjustments + audit cycles. Por ahora solo se trackean entradas (purchase) y salidas (sale), sin transfers internos.

📌 **DESPUÉS 5**: Reorder automation (alert UI cuando `quantity_available < par_level`, con احتمال de auto-crear PO). Por ahora: lectura manual por gerente.

📌 **DESPUÉS 6**: Multi-property consolidated reporting (roll-up de los 5 hoteles). Por ahora: consulta per-`prop_id`.

📌 **DESPUÉS 7**: Integración SAP/QuickBooks/Odoo. Por ahora: hotel está aislado.

📌 **DESPUÉS 8**: Auditoría física (ciclos de recuentos ciegos). Por ahora: ajuste manual via `quantity_available` fix.

---



---

## 7. Riesgos

> ⚠️ **OBSOLETE — ver §15 (trade-offs justificados).** Esta sección enumera riesgos del plan pre-pivote (Opción C con collections nuevas). Los trade-offs de la arquitectura final están consolidados en **§15.3** y “lo que NO se hace” en **§15.4**. **NO es la fuente de verdad** para riesgos.

| Riesgo | Mitigación |
|---|---|
| Sobredimensionar el MVP con Materials Control estilo OPERA | Mantener Fase 0-4 como MVP, Fase 5-8 como iteraciones posteriores. Capacidad de decir "alto" en cualquier fase. |
| Romper migraciones existentes al extender `hotel_products` | Preferir Opción 0c (collections nueva coexistente) — zero impacto en flows existentes |
| Cobrar doble al huésped (cargo en `additional_charges` Y descuento en stock) | Wiring Fase 5 debe ser idempotente + auditado en ambos lados |
| Ledger desbalanceado (consume no encuentra cuenta 5100) | Bloquear wiring si cuenta no existe. `5110 - Costo de amenities` debe seedearse ANTES de Fase 7 |
| Performance con miles de movimientos | Indexes en `(prop_id, product_id, performed_at)` + TTL opcional 90 días para movimientos antiguos en bulk |
| Pérdida de auditoría si `inventory_stock_movements` se borra por error | Colección inmutable (sin update), solo inserts. Backups MongoDB frecuentes |

---

## 8. Métricas de éxito (cómo saber si vale la pena)

> ⚠️ **OBSOLETE — ver §16 (métricas del plan activo).** Esta sección mide el éxito del plan pre-pivote. Las métricas concretas del feature activo (costo poblado, COGS, valor de inventario) viven en los reportes definidos en **§16.9**. **NO es la fuente de verdad** para métricas de éxito.

Medibles a 60-90 días post-lanzamiento:

- % de amenidades con `unit_cost` poblado (>80% = objetivo)
- # de proveedores catalogados con pago recurrente (>5 = madurez)
- # de consumos diarios auto-registrados desde housekeeping (>50% = automatización efectiva)
- COGS total / revenue total (debe calcularse por primera vez — antes era invisible)
- Valor de inventario vs ROI (si > X, justifica mantener)

---

## 10. Plan pivotado: extender existentes, no crear nuevas

### 10.1 Schema extendido `hotel_products`

```python
{
  "_id": ObjectId,
  "prop_id": int,
  "hotel_id": ObjectId,             # FK → dim_hotels._id via resolve_hotel_id()
  "product_id": "PROD-...",          # human-readable, ya existe
  "name": str,
  "description": str,
  "category": str,                  # cambiar a discriminated union (ver §10.2)
  # ─── NUEVOS ────────────────────────────
  "cost_price": float,              # lo que le costó al hotel
  "type": "retail" | "supply" | "asset",  # discriminador (ver §10.2)
  "default_supplier": str | None,   # texto libre == expense_invoices.vendor_name (DESPUÉS → FK)
  "supplier_sku": str | None,       # SKU del proveedor
  "par_level": float | None,        # para alertas (DESPUÉS)
  # ─── EXISTENTES ────────────────────────────
  "unit_price": float,              # retail — se mantiene
  "quantity_available": float,      # ya decrementa en add_booking_line_item
  "is_active": bool,
  "created_at": datetime,
  "created_by": str,
  "updated_at": datetime,
  "seed_source": str | None,
}
```

**Migración** (1 línea + 1 script):
```python
db.hotel_products.update_many(
    {"type": {"$exists": False}},
    {"$set": {"type": "retail", "cost_price": 0.0}}
)
```

### 10.2 Type discriminador

- `"retail"`: producto que se vende al huésped (Minibar, Late checkout, Spa) — `unit_price > 0`
- `"supply"`: producto de consumo interno (jabón housekeeping, guantes, cloro) — `unit_price == 0`
- `"asset"`: durable que se depreció / amortigua (sábanas, colchones, TV) — `unit_price == 0`

La UI puede filtrar por `type` para mostrar solo retail por defecto, supply en sección housekeeping.

### 10.3 `expense_invoices` — NO se extiende

A partir del pivote (round 6), `expense_invoices` queda **intacta**. Sigue siendo el mecanismo para registrar gastos operativos generales (electricidad, payroll, marketing, servicios profesionales).

- NO se le agregan `line_items`
- NO se le agrega `is_internal_supply`
- NO se le agregan hooks de stock automatizados al aprobar

La conexión entre una factura de proveedor y el inventario se resuelve manualmente: el gerente registra la factura en `expense_invoices` (vendor + amount + category + date), y luego hace un **restock explícito** en `/management/products` referenciando el `#invoice` como nota (campo `last_purchase_invoice_ref` que sí existe en `hotel_products`).

Este diseño es el descrito en **§15**. Las secciones §10.4-§10.6 que hablaban de "Hook A al aprobar invoice" y de extender `expense_invoices` han sido reemplazadas por los hooks en §16.4-§16.6 que operan directamente sobre `hotel_products` + ledger.

### 10.4 Hooks (reemplazados por §16.4-§16.6)

Los hooks originales (Hook A al aprobar `expense_invoice`, Hook B al vender) han sido **reemplazados** por una versión más simple y realista en **§16**:

- §16.4 — `POST /products/hotels/{prop_id}/{product_id}/restock` (manual, gerencia)
- §16.5 — extensión de `add_booking_line_item` con COGS posting automático (DR 5110 / CR 1050)
- §16.6 — extensión de `remove_booking_line_item` con reversal automático

Todos usan el helper `post_journal_entry()` que se agrega a `ledger_hooks.py` en Fase 3 (ver §16.4). NO involucran a `expense_invoices` de ninguna manera.

### 10.5 Cuenta ledger nueva required

| Code | Name | Type | Side | Parent |
|---|---|---|---|---|
| `5110` | Costo de Amenities Consumidos | expense | debit | `5000` |

Agregar a `seed_chart_of_accounts.py:16`.

### 10.6 UI incremental (no rebuild)

#### Página `/management/products` (ya existe — ubicado en `admin/products` actualmente)

- Pequeño **drugbar** arriba: chip "Retail" / "Supply" / "Activos" filtra el tipo
- Nueva columna "Costo" (manager-only, depende del permiso `inventory.products.cost.read`)
- Nueva columna "Margen" (manager-only) = `unit_price - cost_price`

#### Página `/management/expenses/invoices/new` (ya existe)

- Nuevo checkbox: **"+ Items de inventario"** que abre un **drag-down** dentro del form
- Si marcado: muestra mini-table donde seleccionar `hotel_product` + `qty` (`unit_cost` autocompletado, Gerente puede overridear)
- Al submit line_items actualiza la collection + hook fires
- Validación backend: `sum(line_items.subtotal) == amount`

### 10.7 Patrón canónico (validado por existir en codebase)

Para `hotel_products` y `expense_invoices`:

```python
# patrón ya validado (migrate_fk_hotel_id.py confirma)
{
  "_id": ObjectId,
  "prop_id": int,              # int scalar (scope por propiedad)
  "hotel_id": ObjectId,        # FK → dim_hotels._id via resolve_hotel_id()
  # ...
}
```

---

### 10.8 Aclaración sobre `product_id` (NO se modifica)

El plan original proponía cambiar el formato a `PROD-YYYYMMDD-NNNN-XXXX`. **Tras el pivote, esto ya no es necesario** porque no hay nuevos `inventory_products` que crear.

El actual `PROD-{token_hex(4)}` se mantiene. Si en el futuro agregás una FK collection (`inventory_suppliers`), ahí sí considera el formato extenso.

---



## 12. Orden sugerido de implementación (FINAL, post-pivote)

Empezando por el schema (los datos limpios antes que cualquier feature):

1. **Fase 1 — Schema extension de `hotel_products`** (~3-5 días)
   - Agregar `cost_price`, `type`, `default_supplier`, `supplier_sku`, `par_level`, `last_purchase_*`, `archived_at/by`, `updated_by` a `hotel_products`
   - **NO** se extiende `expense_invoices`
   - Migración `update_many` con default `type="retail"` + `cost_price=0`
   - Seed ETL: extender `seed_hotel_products.py` con costos demo

2. **Fase 2 — Permissions + cuenta ledger** (~1 día)
   - 2 permisos nuevos: `inventory.products.cost.read`, `inventory.products.cost.manage`
   - Agregar `5110 - Costo de Amenities Consumidos` a `seed_chart_of_accounts.py`

3. **Fase 3 — Hooks** (~3-5 días)
   - Hook A: aprobar `expense_invoice` con `is_internal_supply=True` → +stock + ledger
   - Hook B: extender `add_booking_line_item` con ledger COGS posting (DR 5110 / CR 1050)
   - Hook C: extender `remove_booking_line_item` con reversal
   - Tests unitarios de cada hook

4. **Fase 4 — UI incremental** (~3-5 días)
   - Filtro tipo en `/management/products` + columnas cost/margin
   - Mini-table de items en `/management/expenses/invoices/new`

5. **Fase 5 — Reportes + audit** (~2-3 días)
   - Reporte COGS por período desde ledger entries
   - Reporte margen por producto
   - Valor de inventario (sum quantity_available * cost_price)

6. **Backlog DESPUÉS** — Locations, suppliers FK, movements, reorder, multi-property, etc.

**Total: ~2 sprints** (en lugar de los 2-3 originales con collections nuevas).

---

## 13. Resumen ejecutivo del pivote (TL;DR) — actualizado round 4

**Antes** (round 1-2): crear 5-6 collections nuevas (`inventory_products`, `inventory_suppliers`, `inventory_locations`, `inventory_stock_levels`, `inventory_stock_movements`, `inventory_purchase_orders`).

**Ahora** (post-pivote round 3-4): 
- Extender 2 collections existentes (`hotel_products` + `expense_invoices`) con +5 campos
- Crear 1 hook service que conecta las dos en 3 lugares (purchase, sale, removal)
- Crear 1 cuenta ledger nueva (`5110`)
- Crear 2 permisos granulares nuevos (`cost.read`, `cost.manage`)
- Construir UI desde cero para `hotel_products` (módulo `features/products/` con list + form)
- Extender UI de `/management/expenses/invoices/new` con drag-down de items

**Ventajas del pivote**:
- ~50-60% menos código nuevo (original 70% pero ahora sin UI previa)
- Zero colección nueva → zero impacto en aprendibilidad del modelo
- Refuerza el código existente (`add_booking_line_item`, `expense_invoices`, `hotel_products`) en vez de crear duplicados
- Cierra el mensaje fantasma en `rd-product-modal.ts:45` ("Configurá los productos en Gestión > Productos")
- 1-2 sprints total (vs 6-9 de A, 2-3 de C original)

**Próximo paso concreto** (cuando confirmes arriba):

1. Crear `migrate_add_inventory_fields.py` — backfill `type="retail"` + `cost_price=0` (y resto de campos nuevos) en `hotel_products` existentes
2. Modificar `seed_hotel_products.py` para incluir `cost_price` + `type` en el seed demo
3. Modificar `seed_chart_of_accounts.py` para agregar `5110 - Costo de Amenities Consumidos`
4. Agregar `post_journal_entry()` helper en `server/src/app/modules/expenses/service/ledger_hooks.py` (wrapper simple sobre `_insert_entry` + `_journal_seq`)
5. Crear `frontend/src/app/features/products/` desde cero (BUILD no incremental)
6. Mover `products-api.service.ts` desde `admin/` a `products/` (semánticamente correcto)

Esto es el "schema first + UI from scratch" requerido antes de tocar ningún hook.

---

## 14. Hallazgo round 4: UI faltante de `hotel_products`

**Pregunta del usuario:** "yo no tengo permiso o no existe UI para hotel_products? que hace esa UI si dices q su ruta es esa"

**Respuesta:** UI dedicada NO existe. El mensaje fantasma en `rd-product-modal.ts:45` invita al usuario a "/management/products" pero esa ruta no está implementada. Solo el backend CRUD + el frontend service existen.

### Lo que SÍ existe

| Componente | Ubicación | Función |
|---|---|---|
| Backend CRUD endpoints | `server/src/app/modules/partner/routes/hotel_products.py` | GET, POST, PUT, DELETE |
| Backend service layer | `server/src/app/modules/partner/services/hotel_products.py` | list/create/update/delete + book-related helpers |
| Frontend service | `frontend/src/app/features/admin/services/products-api.service.ts` | HTTP wrapper sobre el backend |
| Reservation modal | `reservation-detail-page/partials/rd-product-modal.ts` | Solo READ del catálogo para agregarlo a reserva |

### Lo que NO existe

- Página Angular donde un usuario con permisos pueda:
  - Listar todos los productos del hotel
  - Crear un nuevo producto (con cost, supplier, category, type, par_level)
  - Editar un producto existente
  - Desactivar un producto (soft delete)
  - Ver stock actual por producto

### Cómo se manages hoy

| Camino | Quién lo hace | Fricción |
|---|---|---|
| `python scripts/seed_hotel_products.py` | Seed inicial | Solo al bootstrap, no runtime |
| `POST /api/management/products/hotels/{prop_id}` con curl | Devs | No-friendly para gerente |
| Postman / API client | Devs | Requiere auth + spec |

### Implicación para el plan

Originalmente Fase 4 declaraba "incremental" porque pensaba que la UI existía. **Es BUILD**. Nueva sección §5 Fase 4 reescrita completa con detalle de archivos a crear, rutas a registrar, sidebar entry, permisos granulares nuevos.

Esto encarece el sprint vs. estimación previa, pero el delta sigue siendo mucho menor que la Opción C original (8 collections nuevas + UI completo).

---


---

## 10. Checkpoint al final de cada fase

Al terminar cada fase, validar:

- [ ] `ruff check` sin nuevos errores
- [ ] `mypy` sin nuevos errores
- [ ] Smoke E2E del nuevo flow (POST Crud + GET list)
- [ ] UI funciona en navegador (no console errors, design tokens respetados)
- [ ] Sidebar-nav muestra entradas nuevas según permisos
- [ ] Audit log captura `register_action` en cada create/update/delete

---

## 11. Lo que aún no sé / necesito de ti (pivoteado)

- ☑ **Opción arquitectónica**: confirmado **Opción EXTENDIDA** (no A/B/C, no colecciónes nuevas — extender `hotel_products` + `expense_invoices` con hooks).
- ☐ `type: str` discriminador — ¿`"retail"` (vender al huésped), `"supply"` (housekeeping), `"asset"` (durables) está bien, o prefieres otros valores?
- ☐ Campo `default_supplier` en `hotel_products` — ¿string libre (igual a `expense_invoices.vendor_name`) o FK desde `expense_invoices`?
- ☐ ¿Moving average para `cost_price` o precio del último purchase? (más simple el último, más exacto el moving average con cubic average)
- ☑ **Locations**: confirmado DESPUÉS (no en MVP). Backlog explícito.
- ☑ **Soft delete**: confirmado estándar moderno (is_active + archived_at + archived_by).
- ☑ **`product_id` formato**: extendido a `PROD-YYYYMMDD-NNNN-XXXX` o reemplazar a un OBJETO_id como referencia canónica + `product_id` solo como label. (No requiere decisión ahora — ver §10.6)

---

**Próximo paso sugerido**: arrancar **Fase 1** cuando confirmes arriba + ver si quieres UI (Fase 3) primero o hook (Fase 2) primero. Yo recomendaría **schema first (Fase 1)**, después hooks (Fase 2), después UI (Fase 3).

