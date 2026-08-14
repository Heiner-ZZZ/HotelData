"""Entry point del pipeline M2C en subproceso separado.

El botón "Run pipeline" de la UI lanza este módulo con ``python -m
src.etl.mongo_to_clickhouse.runner`` en un proceso aislado (``Popen`` con
``start_new_session``), de modo que un reinicio del ``--reload`` de uvicorn
(por ejemplo, al editar cualquier archivo) NO mate la corrida en curso: el
subproceso sobrevive, sigue escribiendo el progreso JSON y reporta al
finalizar. Ejecuta el mismo ``run_pipeline()`` programático; solo cambia el
proceso dueño.

El subproceso es dueño del lock ``pipeline_m2c.lock``: lo limpia en su
``finally`` también ante fallos, para no dejar el run colgado.
"""

from __future__ import annotations

import sys
import traceback


def _run_pipeline():
    """Import perezoso del pipeline: si el paquete no carga, el except lo reporta."""
    from src.etl.mongo_to_clickhouse.pipeline import run_pipeline

    return run_pipeline()


def run_subprocess() -> int:
    """Ejecuta el pipeline completo y devuelve el código de salida (0 = ok)."""
    lock_path = None
    try:
        from config.settings import get_settings

        settings = get_settings()
        lock_path = settings.reports_dir / "pipeline_m2c.lock"

        result = _run_pipeline()
        return 0 if result.get("ok") else 1
    except Exception as exc:  # pragma: no cover - estado de error
        traceback.print_exc()
        try:
            from datetime import datetime, timezone

            from src.etl.mongo_to_clickhouse._common import write_json_file
            from src.etl.mongo_to_clickhouse.config import paths

            write_json_file(
                paths()["progress"],
                {
                    "status": "failed",
                    "message": f"Pipeline fallido (subproceso): {exc}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:  # pragma: no cover - el reporte de error es best-effort
            pass
        return 1
    finally:
        if lock_path is not None:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:  # pragma: no cover
                pass


if __name__ == "__main__":
    raise SystemExit(run_subprocess())
