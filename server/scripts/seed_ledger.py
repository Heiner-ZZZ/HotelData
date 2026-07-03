"""
Seed ledger_transactions collection with realistic hotel PMS data.
Run: docker compose exec server python -m scripts.seed_ledger
"""
import random
from datetime import datetime, timedelta, timezone

from src.database.connection import get_database

LEDGER_COLLECTION = "ledger_transactions"

ACCOUNTS = [
    ("4010.ROOM.REV", "Cargo Alojamiento"),
    ("4020.FNB.REV", "Servicio Restaurante"),
    ("4021.FNB.BAR", "Bar y Bebidas"),
    ("4022.FNB.ROOM", "Room Service"),
    ("4030.SPA.REV", "Spa y Bienestar"),
    ("4040.PARK.REV", "Estacionamiento"),
    ("4050.LNDRY.REV", "Lavandería"),
    ("1010.CASH.CC", "Pago Tarjeta Crédito"),
    ("1020.CASH.DB", "Pago Débito"),
    ("1030.CASH.EF", "Pago Efectivo"),
    ("1040.CASH.TR", "Transferencia Bancaria"),
    ("5010.EXP.UTIL", "Servicios Públicos"),
    ("5015.EXP.MNT", "Mantenimiento"),
    ("5020.EXP.CLEAN", "Productos Limpieza"),
    ("5030.EXP.LNDRY", "Lavandería Externa"),
    ("5040.EXP.MKT", "Marketing"),
    ("5050.EXP.ADMIN", "Gastos Administrativos"),
]

USERS = ["SYS_AUTO", "M.DOE", "J.SMITH", "A.LOPEZ", "R.GARCIA", "S.ADMIN"]
STATUSES = ["audited", "audited", "audited", "audited", "pending", "pending", "discrepancy"]

def seed_ledger(prop_id: int = 1, count: int = 80):
    db = get_database()
    existing = db[LEDGER_COLLECTION].count_documents({"prop_id": prop_id})
    if existing > 0:
        print(f"[SKIP] {existing} ledger transactions already exist for prop_id={prop_id}")
        return

    now = datetime.now(timezone.utc)
    folio_counter = 1040
    docs = []
    balance_map: dict[str, float] = {}

    for i in range(count):
        days_ago = count - i
        tx_date = now - timedelta(days=days_ago, hours=random.randint(6, 22),
                                   minutes=random.randint(0, 59))
        is_payment = random.random() < 0.3

        account_code, account_name = random.choice(ACCOUNTS)
        if is_payment:
            account_code = random.choice(["1010.CASH.CC", "1020.CASH.DB", "1030.CASH.EF", "1040.CASH.TR"])
            account_name = {
                "1010.CASH.CC": "Pago Tarjeta Crédito",
                "1020.CASH.DB": "Pago Débito",
                "1030.CASH.EF": "Pago Efectivo",
                "1040.CASH.TR": "Transferencia Bancaria",
            }[account_code]

        # Every ~5 transactions, start a new folio
        if i % 5 == 0:
            folio_counter += 1
        folio_ref = f"F-{folio_counter}"

        description = account_name
        if account_code.startswith("4010"):
            description = f"Cargo Alojamiento Noche {random.randint(1, 5)}"
        elif account_code.startswith("402"):
            description = random.choice([
                "Cena Restaurante", "Desayuno Buffet", "Room Service Cena",
                "Bar Piscina", "Minibar Habitación",
            ])

        debit = 0.0
        credit = 0.0
        amount = round(random.uniform(15, 450), 2)

        if is_payment:
            credit = amount
        else:
            debit = amount

        balance_map[folio_ref] = balance_map.get(folio_ref, 0) + debit - credit

        status = random.choice(STATUSES)

        doc = {
            "tx_date": tx_date,
            "folio_ref": folio_ref,
            "description": description,
            "account_code": account_code,
            "account_name": account_name,
            "debit": debit,
            "credit": credit,
            "status": status,
            "prop_id": prop_id,
            "user": random.choice(USERS),
            "notes": "" if status != "discrepancy" else "Posible duplicado — requiere revisión",
            "created_at": tx_date,
        }
        docs.append(doc)

    if docs:
        db[LEDGER_COLLECTION].insert_many(docs)
        print(f"[OK] Inserted {len(docs)} ledger transactions for prop_id={prop_id}")

    # Also seed for prop_id=2 (multi-hotel testing)
    docs2 = []
    folio_counter2 = 2000
    for i in range(40):
        days_ago = 40 - i
        tx_date = now - timedelta(days=days_ago, hours=random.randint(6, 22),
                                   minutes=random.randint(0, 59))
        if i % 4 == 0: folio_counter2 += 1
        account_code, account_name = random.choice(ACCOUNTS)
        debit = round(random.uniform(10, 300), 2) if not account_code.startswith("10") else 0
        credit = round(random.uniform(10, 300), 2) if account_code.startswith("10") else 0
        docs2.append({
            "tx_date": tx_date,
            "folio_ref": f"F-{folio_counter2}",
            "description": account_name,
            "account_code": account_code,
            "account_name": account_name,
            "debit": debit,
            "credit": credit,
            "status": random.choice(STATUSES),
            "prop_id": 2,
            "user": random.choice(USERS),
            "notes": "",
            "created_at": tx_date,
        })
    if docs2:
        db[LEDGER_COLLECTION].insert_many(docs2)
        print(f"[OK] Inserted {len(docs2)} ledger transactions for prop_id=2")


if __name__ == "__main__":
    seed_ledger(prop_id=1, count=80)
    seed_ledger(prop_id=2, count=40)
