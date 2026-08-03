#!/usr/bin/env python3
"""Audita funciones que podrían devolver ``None`` en lugar de su resultado.

Detecta el mismo patrón de bug que `hotel_rooms_by_type()` en
``partner/services/rooms/queries.py``: una función que construye una
colección local (``items.append(...)``, ``+=``, ``.add``, ``.update``) y
termina sin ``return`` con valor — devolviendo ``None`` implícitamente.

Heurísticas (por prioridad):

1. ``STRONG`` — Sin ``return`` con valor + construye colección local.
   Es el patrón exacto del bug ya corregido.
2. ``MEDIUM`` — Sin ``return`` con valor y la última sentencia del cuerpo
   es ``for``/``while``/asignación (sin construir colección): candidatos a
   revisión manual (pueden ser funciones void intencionales).
3. ``FALLTHROUGH`` — La última sentencia es un ``for``/``while`` cuyo cuerpo
   contiene ``return`` condicional; si el bucle se completa sin matchear,
   la función cae a ``None`` (a veces intencional, a veces bug).

Generadores (``yield``), ``__init__`` y métodos dunder se omiten.

Uso:
    python scripts/audit_missing_returns.py [raíz]  # raíz por defecto: server/src/app/modules
"""

from __future__ import annotations

import ast
import pathlib
import sys


def _builds_local_collection(fn: ast.FunctionDef) -> bool:
    """True si la función muta una colección local (append/+=/add/update)."""
    assigned: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
        elif (
            isinstance(node, (ast.AnnAssign, ast.AugAssign))
            and isinstance(node.target, ast.Name)
        ):
            assigned.add(node.target.id)

    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"append", "add", "update", "extend"}
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in assigned
        ):
            return True
    return False


def _has_return_value(fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Return) and node.value is not None
        for node in ast.walk(fn)
    )


def _has_yield(fn: ast.FunctionDef) -> bool:
    return any(isinstance(node, (ast.Yield, ast.YieldFrom)) for node in ast.walk(fn))


def _returns_in_last_loop(fn: ast.FunctionDef, last: ast.stmt) -> bool:
    """True si hay al menos un ``return`` con valor dentro del bucle final."""
    return any(
        isinstance(node, ast.Return) and node.value is not None
        for node in ast.walk(last)
    )


def _declares_non_none_return(fn: ast.FunctionDef) -> bool:
    """True si la anotación de retorno NO es ``None`` (o es genérica ``list``/``dict``)."""
    returns = fn.returns
    if returns is None:
        return False  # sin anotación -> no podemos inferir intención
    name = ""
    if isinstance(returns, ast.Name):
        name = returns.id
    elif isinstance(returns, ast.Constant) and returns.value is None:
        name = "None"
    elif isinstance(returns, ast.Constant):
        name = str(returns.value)
    elif isinstance(returns, ast.Subscript):
        # list[...] / dict[...] / tuple[...]
        if isinstance(returns.value, ast.Name):
            name = returns.value.id
    elif isinstance(returns, ast.BinOp) and isinstance(returns.op, ast.BitOr):
        # X | None (PEP 604) — es ``dict | None`` → NO es puramente None
        return True
    return name not in ("", "None", "NoneType")


def audit(path: pathlib.Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as exc:
        return [f"PARSE ERROR {path}: {exc}"]

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = node.name
        if name.startswith("__") and name.endswith("__"):
            continue
        if _has_yield(node):
            continue

        body = node.body
        if not body:
            continue
        last = body[-1]

        if not _has_return_value(node):
            declares_non_none = _declares_non_none_return(node)
            if declares_non_none:
                # ⚠️ El patrón del bug real: anota list/dict/... pero nunca retorna.
                hits.append(
                    f"{path}:{node.lineno}: ANNOTATION  {name}() — declara retorno no-None sin return (¡bug!)"
                )
            elif _builds_local_collection(node):
                hits.append(
                    f"{path}:{node.lineno}: STRONG      {name}() — construye colección local y NO retorna"
                )
            elif isinstance(last, (ast.For, ast.While, ast.Assign, ast.AugAssign, ast.AnnAssign)):
                hits.append(
                    f"{path}:{node.lineno}: MEDIUM      {name}() — termina sin return (revisar: ¿void intencional?)"
                )
        elif isinstance(last, (ast.For, ast.While)) and _returns_in_last_loop(node, last):
            # return solo dentro del bucle final -> si no matchea, cae a None
            hits.append(
                f"{path}:{node.lineno}: FALLTHROUGH {name}() — return solo en bucle final (¿None intencional?)"
            )
    return hits


def main() -> int:
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(
        "server/src/app/modules"
    )
    if not root.exists():
        print(f"Ruta no existe: {root}")
        return 2

    files = sorted(root.rglob("*.py"))
    all_hits: list[str] = []
    for path in files:
        all_hits.extend(audit(path))

    print(f"Archivos analizados: {len(files)}")
    print(f"Candidatos: {len(all_hits)}")
    print("=" * 90)
    for hit in all_hits:
        print(hit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
