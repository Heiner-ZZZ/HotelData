"""
Corrections for specs 014-025 based on TAF06 analysis:
1. Routes: /api/partner/ → /api/management/
2. Actors: Align with TAF06 actor-CU matrix

TAF06 actors (9 total):
- Cliente / Viajero
- Recepcionista
- Hotel Partner / Dueño
- Gerente de hotel
- Revenue Manager
- Marketing hotelero
- Super Admin
- Auditor de Datos
- Sistema FastAPI / Airflow
"""

import os

SPECS_DIR = os.path.join(".specify", "specs")

# ============================================================
# ACTOR CORRECTIONS per spec
# Each entry: spec_dir -> list of (old_actor_table_block, new_actor_table_block)
# ============================================================
ACTOR_CORRECTIONS = {
    "014-editar-nombre-comercial": (
        # Old actors block
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Edita nombre comercial de sus propiedades asignadas |\r\n| Gerente de hotel | Edita nombre comercial de las propiedades que gestiona |\r\n| Super Admin | Edita nombre comercial de cualquier propiedad |",
        # New actors block
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Marketing hotelero | Edita nombre comercial y perfil visible de propiedades |\r\n| Hotel partner | Edita nombre comercial de sus propiedades asignadas |"
    ),
    "015-historial-cambios": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Consulta cambios de sus propiedades |\r\n| Gerente de hotel | Consulta cambios de propiedades que gestiona |\r\n| Super Admin | Consulta cambios de cualquier propiedad |\r\n| Auditor de datos | Revisa trazabilidad de cambios |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Auditor de Datos | Revisa trazabilidad de cambios de perfil y contenido |\r\n| Hotel partner | Consulta cambios de sus propias propiedades |"
    ),
    "016-tipos-habitacion": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Crea tipos de habitacion para su propiedad |\r\n| Gerente de hotel | Administra tipos de habitacion de propiedades a su cargo |\r\n| Recepcionista | Consulta tipos de habitacion (solo lectura) |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Crea y gestiona tipos de habitacion para su propiedad |"
    ),
    "017-inventario-disponibilidad": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Actualiza inventario diario |\r\n| Gerente de hotel | Actualiza inventario de propiedades a su cargo |\r\n| Recepcionista | Consulta disponibilidad (solo lectura) |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Gerente de hotel | Actualiza inventario diario de propiedades a su cargo |"
    ),
    "018-bloqueos-disponibilidad": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Crea y elimina bloqueos de disponibilidad |\r\n| Gerente de hotel | Gestiona bloqueos de propiedades a su cargo |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Gerente de hotel | Registra bloqueos de disponibilidad y blackout dates |"
    ),
    "019-planes-tarifarios": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Crea planes tarifarios |\r\n| Revenue manager | Define reglas de tarifa |\r\n| Gerente de hotel | Aprueba planes tarifarios |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Revenue manager | Crea y gestiona planes tarifarios |"
    ),
    "020-tarifas-calendario": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Configura tarifas por fecha |\r\n| Revenue manager | Define precios por temporada |\r\n| Gerente de hotel | Revisa y aprueba tarifas |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Revenue manager | Configura tarifas por fecha y temporada |"
    ),
    "021-promociones-cupones": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Revenue manager | Crea y gestiona campanas promocionales |\r\n| Marketing hotelero | Define descuentos y segmentos objetivo |\r\n| Cliente | Usa codigo de cupon al reservar |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Marketing hotelero | Define descuentos y segmentos objetivo |\r\n| Revenue manager | Crea y gestiona campanas promocionales |"
    ),
    "022-politicas-hoteleras": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Configura politicas de su propiedad |\r\n| Gerente de hotel | Aprueba cambios de politicas |\r\n| Cliente | Consulta politicas antes de reservar |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Configura politicas de su propiedad |"
    ),
    "023-amenities-imagenes": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Hotel partner | Actualiza contenido comercial de su propiedad |\r\n| Marketing hotelero | Mejora descripciones y fotos |\r\n| Gerente de hotel | Aprueba contenido |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Marketing hotelero | Actualiza amenities, imagenes y contenido comercial |"
    ),
    "025-moderacion-resenas": (
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Marketing hotelero | Modera resenas y responde en nombre del hotel |\r\n| Super Admin | Moderacion general del sistema |\r\n| Hotel partner | Responde a resenas de su propiedad |",
        "| Actor | Descripcion |\r\n|-------|-------------|\r\n| Marketing hotelero | Modera y responde resenas |\r\n| Super Admin | Moderacion general del sistema |"
    ),
}

def correct_spec(spec_dir, actor_correction=None):
    spec_path = os.path.join(SPECS_DIR, spec_dir, "spec.md")
    if not os.path.exists(spec_path):
        print(f"  [SKIP] {spec_dir} - file not found")
        return False

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []

    # 1. Route correction: /api/partner/ → /api/management/
    old_routes = content.count("/api/partner/")
    if old_routes > 0:
        content = content.replace("/api/partner/", "/api/management/")
        changes.append(f"    Routes: {old_routes} occurrences corrected")

    # 2. Actor correction
    if actor_correction:
        old_actors, new_actors = actor_correction
        if old_actors in content:
            content = content.replace(old_actors, new_actors)
            changes.append(f"    Actors: corrected")
        else:
            # Try without \r
            old_actors_no_r = old_actors.replace("\r\n", "\n")
            new_actors_no_r = new_actors.replace("\r\n", "\n")
            if old_actors_no_r in content:
                content = content.replace(old_actors_no_r, new_actors_no_r)
                changes.append(f"    Actors: corrected (no \\r format)")
            else:
                changes.append(f"    Actors: COULD NOT MATCH - manual check needed")

    if changes:
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [OK] {spec_dir}")
        for c in changes:
            print(c)
        return True
    else:
        print(f"  [NO CHANGE] {spec_dir}")
        return False


def main():
    print("=" * 60)
    print("CORRECTING ROUTES AND ACTORS IN SPECS 014-025")
    print("=" * 60)

    # Specs that need route corrections (014-023)
    route_specs = [
        "014-editar-nombre-comercial",
        "015-historial-cambios",
        "016-tipos-habitacion",
        "017-inventario-disponibilidad",
        "018-bloqueos-disponibilidad",
        "019-planes-tarifarios",
        "020-tarifas-calendario",
        "021-promociones-cupones",
        "022-politicas-hoteleras",
        "023-amenities-imagenes",
    ]

    print("\n--- Specs with route + actor corrections ---")
    for spec_dir in route_specs:
        actor_correction = ACTOR_CORRECTIONS.get(spec_dir)
        correct_spec(spec_dir, actor_correction)

    # Specs that need only actor corrections (024-025)
    print("\n--- Specs with actor-only corrections ---")
    for spec_dir in ["024-registro-resenas", "025-moderacion-resenas"]:
        actor_correction = ACTOR_CORRECTIONS.get(spec_dir)
        if actor_correction:
            correct_spec(spec_dir, actor_correction)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    # Summary of what was expected
    print("\nExpected changes summary:")
    print("  Routes corrected in: 014, 015, 016, 017, 018, 019, 020, 021, 022, 023")
    print("  Actors corrected in: 014, 015, 016, 017, 018, 019, 020, 021, 022, 023, 025")
    print("  Actors already correct: 024 (Cliente, Sistema)")
    print("\nTAF06 actor mapping:")
    print("  014 CU-O12: Marketing / Partner")
    print("  015 CU-O13: Auditor de Datos / Partner")
    print("  016 CU-O14: Hotel partner")
    print("  017 CU-O15: Gerente hotel")
    print("  018 CU-O16: Gerente hotel")
    print("  019 CU-O17: Revenue manager")
    print("  020 CU-O18: Revenue manager")
    print("  021 CU-O19: Marketing / Revenue")
    print("  022 CU-O20: Hotel partner")
    print("  023 CU-O21: Marketing hotelero")
    print("  024 CU-O22: Cliente")
    print("  025 CU-O23: Marketing / Super Admin")


if __name__ == "__main__":
    main()
