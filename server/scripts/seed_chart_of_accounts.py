"""
Seed chart_of_accounts with standard hotel accounting chart.
Run: docker compose exec server python -m scripts.seed_chart_of_accounts
"""
from src.database.connection import get_database

COLLECTION = "chart_of_accounts"

# Standard hotel chart of accounts (Spanish / LATAM convention)
ACCOUNTS = [
    # 1xxx — Activos
    {"account_code": "1010", "account_name": "Caja General", "account_type": "asset", "normal_balance": "debit", "parent_code": "1000", "level": 2, "description": "Efectivo en caja registradora"},
    {"account_code": "1020", "account_name": "Bancos", "account_type": "asset", "normal_balance": "debit", "parent_code": "1000", "level": 2, "description": "Cuentas bancarias operativas"},
    {"account_code": "1030", "account_name": "Cuentas por Cobrar Huéspedes", "account_type": "asset", "normal_balance": "debit", "parent_code": "1000", "level": 2, "description": "Saldos pendientes de huéspedes (foliados)"},
    {"account_code": "1040", "account_name": "Cuentas por Cobrar Empresas", "account_type": "asset", "normal_balance": "debit", "parent_code": "1000", "level": 2, "description": "Facturas por cobrar a empresas/corporativos"},
    {"account_code": "1050", "account_name": "Inventario", "account_type": "asset", "normal_balance": "debit", "parent_code": "1000", "level": 2, "description": "Inventario de amenities, suministros, alimentos"},

    # 2xxx — Pasivos
    {"account_code": "2010", "account_name": "Cuentas por Pagar Proveedores", "account_type": "liability", "normal_balance": "credit", "parent_code": "2000", "level": 2, "description": "Obligaciones con proveedores de bienes y servicios"},
    {"account_code": "2020", "account_name": "Impuestos por Pagar", "account_type": "liability", "normal_balance": "credit", "parent_code": "2000", "level": 2, "description": "IVA, ISH, y otros impuestos recaudados por pagar"},
    {"account_code": "2030", "account_name": "Depósitos de Huéspedes", "account_type": "liability", "normal_balance": "credit", "parent_code": "2000", "level": 2, "description": "Anticipos y garantías recibidas de huéspedes"},

    # 3xxx — Patrimonio
    {"account_code": "3010", "account_name": "Capital", "account_type": "equity", "normal_balance": "credit", "parent_code": "3000", "level": 2, "description": "Capital social del hotel"},

    # 4xxx — Ingresos
    {"account_code": "4010", "account_name": "Ingresos por Alojamiento", "account_type": "revenue", "normal_balance": "credit", "parent_code": "4000", "level": 2, "description": "Ingresos por venta de habitaciones (room revenue)"},
    {"account_code": "4020", "account_name": "Ingresos por Alimentos y Bebidas", "account_type": "revenue", "normal_balance": "credit", "parent_code": "4000", "level": 2, "description": "Restaurante, bar, room service, minibar"},
    {"account_code": "4030", "account_name": "Ingresos por Servicios", "account_type": "revenue", "normal_balance": "credit", "parent_code": "4000", "level": 2, "description": "Spa, parking, lavandería, llamadas, mascotas"},
    {"account_code": "4040", "account_name": "Otros Ingresos Operativos", "account_type": "revenue", "normal_balance": "credit", "parent_code": "4000", "level": 2, "description": "Late check-out, daños cobrados, alquiler de equipos"},

    # 5xxx — Costos y Gastos
    {"account_code": "5010", "account_name": "Costo de Ventas F&B", "account_type": "expense", "normal_balance": "debit", "parent_code": "5000", "level": 2, "description": "Costo de alimentos y bebidas vendidos"},
    {"account_code": "5020", "account_name": "Gastos de Personal", "account_type": "expense", "normal_balance": "debit", "parent_code": "5000", "level": 2, "description": "Sueldos, salarios, beneficios del personal"},
    {"account_code": "5030", "account_name": "Gastos Operativos", "account_type": "expense", "normal_balance": "debit", "parent_code": "5000", "level": 2, "description": "Servicios públicos, mantenimiento, limpieza, lavandería externa"},
    {"account_code": "5040", "account_name": "Gastos de Marketing", "account_type": "expense", "normal_balance": "debit", "parent_code": "5000", "level": 2, "description": "Publicidad, comisiones OTAs, campañas"},
    {"account_code": "5050", "account_name": "Gastos Administrativos", "account_type": "expense", "normal_balance": "debit", "parent_code": "5000", "level": 2, "description": "Papelería, licencias, honorarios, seguros"},

    # 6xxx — Descuentos y Ajustes (cuentas de contrapartida)
    {"account_code": "6010", "account_name": "Descuentos por Promoción", "account_type": "contra_revenue", "normal_balance": "debit", "parent_code": "6000", "level": 2, "description": "Descuentos comerciales y promociones aplicadas"},
    {"account_code": "6020", "account_name": "Ajustes por Cortesía", "account_type": "contra_revenue", "normal_balance": "debit", "parent_code": "6000", "level": 2, "description": "Cortesías, ajustes por quejas, cargos reversados"},
    {"account_code": "6030", "account_name": "Cargos Reversados", "account_type": "contra_revenue", "normal_balance": "debit", "parent_code": "6000", "level": 2, "description": "Reversión de cargos facturados por error"},
]


def seed():
    db = get_database()
    existing = db[COLLECTION].count_documents({})
    if existing > 0:
        print(f"[SKIP] {existing} chart of accounts already exist")
        return

    db[COLLECTION].insert_many(ACCOUNTS)
    print(f"[OK] Inserted {len(ACCOUNTS)} chart of accounts")


if __name__ == "__main__":
    seed()
