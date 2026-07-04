"""Server-side report generation: PDF (WeasyPrint) and XLSX (OpenPyXL).

The frontend builds an HTML document (full HTML5+CSS3, including @media print
or sends structured workbook data) and POSTs it to these endpoints. The
backend returns a binary blob the browser saves as a file.
"""
