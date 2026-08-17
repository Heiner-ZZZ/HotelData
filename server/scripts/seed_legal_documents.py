"""Seed canónico de documentos legales versionados (Términos y Condiciones).

Los textos legales NUNCA viven hardcodeados en el frontend: se publican a la
colección ``legal_documents`` (doc_type + version + sections JSON) y las UI
los consumen desde ``GET /api/public/legal``.

Idempotencia: por cada ``doc_type`` solo siembra la versión v1 si NO existe
ninguna versión. Si ya hay versiones publicadas (v2+ por el panel admin), NO
las pisa — el histórico y la vigencia los controla el admin.

Uso:
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \
        python -m scripts.seed_legal_documents
    # o con la BD de test (diagnóstico aislado):
    MONGO_DATABASE=hoteldata_hub_test ... python -m scripts.seed_legal_documents
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from pymongo import MongoClient

DOCUMENTS = [
    {
        "doc_type": "terms_guest",
        "title": "Términos y Condiciones para Huéspedes",
        "sections": [
            {
                "heading": "1. Aceptación de los términos",
                "body": (
                    "Al crear una cuenta, realizar una reserva o usar la plataforma "
                    "HotelData, aceptas estos Términos y Condiciones en su versión "
                    "vigente. Si no estás de acuerdo con alguna parte, no utilices "
                    "los servicios. La versión aceptada queda registrada en tu cuenta "
                    "con fecha y hora."
                ),
            },
            {
                "heading": "2. Registro de cuenta y verificación",
                "body": (
                    "Para reservar necesitas una cuenta con un correo válido. Eres "
                    "responsable de mantener la confidencialidad de tu contraseña y "
                    "de la actividad que ocurra en tu cuenta. La información que "
                    "proporciones debe ser veraz y actual; el uso de identidades "
                    "falsas puede derivar en la cancelación de reservas."
                ),
            },
            {
                "heading": "3. Reservas y precios",
                "body": (
                    "Los precios mostrados corresponden a las tarifas vigentes "
                    "publicadas por cada alojamiento, en la moneda seleccionada. Una "
                    "reserva se considera confirmada cuando el alojamiento la acepta "
                    "y recibes la confirmación por correo. HotelData actúa como "
                    "plataforma de intermediación: el contrato de hospedaje se "
                    "celebra entre tú y el alojamiento."
                ),
            },
            {
                "heading": "4. Pagos y depósitos",
                "body": (
                    "Algunos alojamientos exigen un depósito por adelantado que "
                    "podrás pagar en efectivo o con tarjeta. El depósito exigido se "
                    "informa antes de confirmar la reserva y se aplica contra el "
                    "saldo total de tu estancia. Los pagos registrados quedan "
                    "documentados en tu folio de facturación."
                ),
            },
            {
                "heading": "5. Cancelaciones y reembolsos",
                "body": (
                    "Las condiciones de cancelación son las publicadas por cada "
                    "alojamiento al momento de reservar. Si cancelas dentro de la "
                    "ventana permitida, el depósito se reembolsa conforme a esas "
                    "condiciones. Los reembolsos se procesan contra el método de "
                    "pago original; el plazo puede variar según la entidad emisora."
                ),
            },
            {
                "heading": "6. Check-in y estancia",
                "body": (
                    "El check-in se realiza con una identificación oficial. Debes "
                    "respetar las políticas de la propiedad: horarios, aforo, "
                    "mascotas, fumadores y el uso de las instalaciones. El "
                    "incumplimiento reiterado puede derivar en la terminación "
                    "anticipada de la estancia sin derecho a reembolso."
                ),
            },
            {
                "heading": "7. Conducta y responsabilidades",
                "body": (
                    "Eres responsable de los daños que causes a las instalaciones "
                    "durante tu estancia. El alojamiento puede cargar los daños "
                    "justificados a tu folio. Queda prohibido el uso de los "
                    "servicios para actividades ilícitas."
                ),
            },
            {
                "heading": "8. Datos personales y privacidad",
                "body": (
                    "Tratamos tus datos personales conforme a nuestra Política de "
                    "Privacidad, que forma parte de estos términos. Puedes ejercer "
                    "tus derechos de acceso, rectificación, cancelación y oposición "
                    "escribiendo a soporte."
                ),
            },
            {
                "heading": "9. Limitación de responsabilidad",
                "body": (
                    "HotelData pondrá el máximo cuidado en el funcionamiento de la "
                    "plataforma, pero no garantiza su disponibilidad ininterrumpida. "
                    "La responsabilidad de la plataforma se limita a la operación "
                    "del servicio; la prestación del hospedaje es responsabilidad "
                    "exclusiva del alojamiento."
                ),
            },
            {
                "heading": "10. Modificaciones",
                "body": (
                    "Podemos actualizar estos términos cuando lo requiera la "
                    "normativa o el servicio. Las modificaciones se publican en "
                    "esta sección con una nueva versión; las reservas ya "
                    "confirmadas se rigen por la versión vigente al momento de "
                    "reservar."
                ),
            },
            {
                "heading": "11. Ley aplicable",
                "body": (
                    "Estos términos se rigen por la legislación del país donde se "
                    "ubica el alojamiento. Para cualquier controversia, las partes "
                    "se someten a los tribunales competentes de dicha jurisdicción."
                ),
            },
        ],
    },
    {
        "doc_type": "terms_hotel_partner",
        "title": "Términos y Condiciones para Anfitriones",
        "sections": [
            {
                "heading": "1. Aceptación",
                "body": (
                    "Al registrar tu alojamiento en HotelData aceptas estos "
                    "Términos para Anfitriones en su versión vigente. La versión "
                    "aceptada queda registrada en tu cuenta de anfitrión y en el "
                    "expediente de tu propiedad con fecha y hora."
                ),
            },
            {
                "heading": "2. Registro y aprobación",
                "body": (
                    "Tu alojamiento se registra y queda pendiente de aprobación "
                    "por el administrador de la plataforma. Durante ese periodo "
                    "puedes consultar el estado de tu registro, pero la propiedad "
                    "no opera hasta su activación. La aprobación no exime del "
                    "cumplimiento de la normativa local aplicable a tu negocio."
                ),
            },
            {
                "heading": "3. Suscripción y facturación",
                "body": (
                    "El uso de la plataforma se rige por un plan de suscripción "
                    "derivado de la cantidad de habitaciones declaradas. La "
                    "primera factura vence 7 días después de la aprobación del "
                    "alojamiento y las siguientes conforme al ciclo elegido "
                    "(mensual o anual). El impago puede derivar en la suspensión "
                    "del servicio."
                ),
            },
            {
                "heading": "4. Tarifas y comisiones",
                "body": (
                    "Las tarifas que publicas son de tu responsabilidad y deben "
                    "incluir los impuestos aplicables. La plataforma puede cobrar "
                    "una comisión sobre las transacciones intermediadas conforme a "
                    "la configuración vigente. Cualquier cambio de comisión se te "
                    "notificará con antelación."
                ),
            },
            {
                "heading": "5. Obligaciones del anfitrión",
                "body": (
                    "Debes mantener actualizados tus datos, la disponibilidad, las "
                    "tarifas y las políticas de tu propiedad. Las reservas "
                    "confirmadas deben honrarse; la cancelación injustificada "
                    "afecta la reputación de tu alojamiento y puede derivar en "
                    "penalizaciones."
                ),
            },
            {
                "heading": "6. Contenido y propiedad intelectual",
                "body": (
                    "Al publicar fotos, descripciones u otro contenido, otorgas a "
                    "la plataforma una licencia para exhibirlo con fines de "
                    "comercialización. El contenido debe ser veraz, no engañoso y "
                    "no infringir derechos de terceros."
                ),
            },
            {
                "heading": "7. Veracidad de la información",
                "body": (
                    "La información declarada (habitaciones, servicios, "
                    "instalaciones) debe coincidir con la realidad. La "
                    "divergencia reiterada entre lo publicado y lo ofrecido puede "
                    "derivar en la suspensión temporal o definitiva del "
                    "alojamiento."
                ),
            },
            {
                "heading": "8. Suspensión y cancelación del servicio",
                "body": (
                    "La plataforma puede suspender tu cuenta ante incumplimientos "
                    "graves de estos términos o de la normativa. Puedes solicitar "
                    "la baja en cualquier momento; los cargos ya facturados no son "
                    "reembolsables salvo disposición legal en contrario."
                ),
            },
            {
                "heading": "9. Responsabilidad",
                "body": (
                    "Eres el responsable último de la operación de tu alojamiento: "
                    "atención al huésped, facturación local, seguridad y "
                    "cumplimiento normativo. La plataforma no asume la prestación "
                    "del servicio de hospedaje."
                ),
            },
            {
                "heading": "10. Modificaciones y ley aplicable",
                "body": (
                    "Podemos actualizar estos términos publicando una nueva "
                    "versión. Las condiciones comerciales vigentes (plan, comisión) "
                    "se conservan hasta el final del ciclo de facturación en curso. "
                    "Las controversias se someten a la legislación del país donde "
                    "se ubica el alojamiento."
                ),
            },
        ],
    },
    {
        "doc_type": "privacy_policy",
        "title": "Política de Privacidad",
        "sections": [
            {
                "heading": "1. Responsable del tratamiento",
                "body": (
                    "HotelData es responsable del tratamiento de los datos "
                    "personales recopilados a través de la plataforma, tanto de "
                    "huéspedes como de anfitriones. Para cualquier consulta "
                    "escríbenos a soporte@hoteldata.local."
                ),
            },
            {
                "heading": "2. Datos que recopilamos",
                "body": (
                    "Recopilamos los datos que nos proporcionas al registrarte "
                    "(nombre, correo, usuario, contraseña cifrada), los datos de "
                    "tu alojamiento si eres anfitrión (ubicación, teléfono, "
                    "habitaciones) y los datos de uso de la plataforma (reservas, "
                    "pagos, preferencias)."
                ),
            },
            {
                "heading": "3. Finalidad del tratamiento",
                "body": (
                    "Tus datos se utilizan para crear y gestionar tu cuenta, "
                    "procesar reservas y pagos, verificar tu identidad, prevenir "
                    "fraude, mejorar el servicio y enviarte comunicaciones "
                    "operativas. No utilizamos tus datos para finalidades "
                    "incompatibles con las aquí descritas."
                ),
            },
            {
                "heading": "4. Base legal",
                "body": (
                    "Tratamos tus datos con base en la ejecución del contrato de "
                    "servicio (registro, reservas), el consentimiento que otorgas "
                    "al aceptar esta política y, en su caso, el cumplimiento de "
                    "obligaciones legales del operador."
                ),
            },
            {
                "heading": "5. Compartición de datos",
                "body": (
                    "Compartimos los datos estrictamente necesarios con el "
                    "alojamiento cuando realizas una reserva (nombre, contacto, "
                    "fechas) y con proveedores de infraestructura (alojamiento, "
                    "correo) bajo acuerdos de confidencialidad. No vendemos tus "
                    "datos personales."
                ),
            },
            {
                "heading": "6. Conservación",
                "body": (
                    "Conservamos tus datos mientras tu cuenta esté activa y "
                    "durante los plazos legales de conservación aplicables (por "
                    "ejemplo, registros de facturación y auditoría). Al eliminar "
                    "tu cuenta, los datos se anonimizan o suprimen conforme a la "
                    "ley."
                ),
            },
            {
                "heading": "7. Derechos del titular",
                "body": (
                    "Puedes ejercer tus derechos de acceso, rectificación, "
                    "cancelación y oposición (ARCO) sobre tus datos personales "
                    "escribiendo a soporte@hoteldata.local. Atenderemos tu "
                    "solicitud dentro de los plazos establecidos por la "
                    "legislación aplicable."
                ),
            },
            {
                "heading": "8. Seguridad",
                "body": (
                    "Aplicamos medidas técnicas y organizativas adecuadas: "
                    "contraseñas cifradas, sesiones con expiración, control de "
                    "accesos por roles y registros de auditoría. Ningún sistema es "
                    "infalible; ante una brecha de seguridad notificaremos a los "
                    "afectados y a la autoridad competente cuando la ley lo exija."
                ),
            },
            {
                "heading": "9. Cookies y datos de navegación",
                "body": (
                    "La plataforma utiliza cookies estrictamente necesarias para el "
                    "funcionamiento de la sesión. No empleamos cookies de "
                    "publicidad de terceros. Puedes configurar tu navegador para "
                    "rechazarlas, aunque algunas funciones podrían dejar de "
                    "funcionar."
                ),
            },
            {
                "heading": "10. Contacto y actualizaciones",
                "body": (
                    "Esta política puede actualizarse para reflejar cambios "
                    "normativos o del servicio; la versión vigente se publica en "
                    "esta sección. Para cualquier consulta sobre tus datos, "
                    "escríbenos a soporte@hoteldata.local."
                ),
            },
        ],
    },
]


def seed(uri: str = "mongodb://localhost:27018", db_name: str = "hoteldata_hub") -> None:
    client = MongoClient(uri)
    try:
        db = client[db_name]
        if "legal_documents" not in db.list_collection_names():
            db.create_collection("legal_documents")
        # Mismos nombres de índice que ``ensure_legal_collections`` (app): un
        # create_index con el MISMO nombre es idempotente; con nombre distinto
        # para las mismas keys lanza IndexOptionsConflict en Mongo.
        db.legal_documents.create_index(
            [("doc_type", 1), ("version", 1)],
            unique=True,
            name="idx_legal_doc_type_version",
        )
        db.legal_documents.create_index(
            [("doc_type", 1), ("is_active", 1)],
            name="idx_legal_active",
        )

        now = datetime.now(timezone.utc)
        seeded = 0
        skipped = 0
        for doc in DOCUMENTS:
            existing = db.legal_documents.find_one({"doc_type": doc["doc_type"]})
            if existing:
                print(
                    f"[skip] {doc['doc_type']}: ya existe v{existing['version']} "
                    f"(no se pisan versiones publicadas)"
                )
                skipped += 1
                continue
            # Desactivar cualquier versión activa previa del mismo tipo (no debería
            # haber ninguna si es la primera siembra, pero por seguridad).
            db.legal_documents.update_many(
                {"doc_type": doc["doc_type"], "is_active": True},
                {"$set": {"is_active": False}},
            )
            db.legal_documents.insert_one(
                {
                    "doc_type": doc["doc_type"],
                    "version": 1,
                    "title": doc["title"],
                    "effective_date": now,
                    "is_active": True,
                    "sections": doc["sections"],
                    "created_at": now,
                    "updated_by": "system-seed",
                }
            )
            print(f"[seed] {doc['doc_type']}: v1 «{doc['title']}» ({len(doc['sections'])} secciones)")
            seeded += 1

        print(f"\nDone! {seeded} documento(s) sembrado(s), {skipped} omitido(s).")
    finally:
        client.close()


if __name__ == "__main__":
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    db_name = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    seed(uri, db_name)
