# Conversión Markdown → .docx (TA12)

Esta carpeta contiene los scripts para convertir `docs/library/TA12.md` (y cualquier Markdown general) a un `.docx` con **diseño de tablas de Word** real (bordes, encabezado con banda, autoajuste).

## Contenido

| Archivo | Función |
|---------|---------|
| `convert_md_to_docx.py` | Script principal. Hace el pipeline completo (pandoc + python-docx). |

## Cómo se usa

```bash
# Convertir TA12.md → TA12.docx (salida por defecto)
py scripts/docx_conversion/convert_md_to_docx.py docs/library/TA12.md

# O especificando salida explícita
py scripts/docx_conversion/convert_md_to_docx.py docs/library/TA12.md docs/library/TA12.docx

# Reutilizable con cualquier Markdown
py scripts/docx_conversion/convert_md_to_docx.py cualquier_archivo.md ruta/salida.docx
```

## Pipeline (2 pasos)

### [1/2] Pandoc — conversión base (preserva TODO)
`pandoc TA12.md -o TA12.docx --wrap=preserve --toc --toc-depth=3`

Pandoc convierte nativamente Markdown a .docx. **No se pierde ningún detalle**:
- Encabezados (#..######), listas, blockquotes, párrafos
- Tablas Markdown (`| col | col |` → tabla real de Word, no pipes visibles)
- Code blocks (fenced y con indentación)
- Formato inline (negrita, cursiva, código)
- Emojis y caracteres Unicode
- Tabla de contenidos automática (TOC, profundidad 3)

### [2/2] Python-docx — diseño visual de las tablas
Se recorre cada tabla del `.docx` y se aplica:
- **Bordes finos grises** (color `#6F6F6F`, 0.5 pt) en todas las celdas
- **Encabezado en negrita + banda gris** (`#E7E6E6`) en la primera fila
- **Autoajuste de columnas** al contenido

> Nota: solo se modifica el estilo visual de las tablas. Ningún texto del Markdown se altera, elimina o reordena.

## Requisitos

- **Pandoc 3.x** (instalado en el sistema / Docker)
- **Python 3.x** con `python-docx` instalado (`py -m pip install python-docx`)

## Verificación post-conversión

Después de ejecutar la conversión, puede verificar:

```bash
# 1. El archivo existe y tiene tamaño razonable
ls -la docs/library/TA12.docx

# 2. Con python-docx: confirmar conteo de tablas y secciones
py -c "
from docx import Document
d = Document('docs/library/TA12.docx')
print('Tablas:', len(d.tables))
print('Párrafos:', len(d.paragraphs))
print('Secciones:', len(d.sections))
"
```

## Notas

- Si Pandoc no está instalado, instalar desde [pandoc.org](https://pandoc.org/installing.html) o vía `winget install JohnMacFarlane.Pandoc`.
- Si `python-docx` falla al importar, reinstalar: `py -m pip install --upgrade python-docx`.
- El script es **idempotente**: ejecutarlo varias veces sobre el mismo `.md` produce el mismo `.docx`.
