import markdown
from weasyprint import HTML, CSS
import sys
import os

md_path = r"C:\Users\Dianne\Downloads\project_proposal.md"
pdf_path = r"C:\Users\Dianne\Downloads\project_proposal.pdf"

with open(md_path, 'r', encoding='utf-8') as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

css = CSS(string="""
    @page {
        size: A4;
        margin: 2cm 2.5cm;
    }
    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.7;
        color: #1a1a2e;
    }
    h1 {
        font-size: 20pt;
        color: #003366;
        border-bottom: 3px solid #FFCC00;
        padding-bottom: 8px;
        margin-top: 0;
    }
    h2 {
        font-size: 14pt;
        color: #003366;
        border-left: 4px solid #FFCC00;
        padding-left: 10px;
        margin-top: 28px;
    }
    h3 {
        font-size: 12pt;
        color: #003366;
        margin-top: 18px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 10pt;
    }
    th {
        background-color: #003366;
        color: white;
        padding: 8px 10px;
        text-align: left;
    }
    td {
        padding: 7px 10px;
        border-bottom: 1px solid #dde3ed;
    }
    tr:nth-child(even) td {
        background-color: #f4f7fc;
    }
    p {
        margin: 8px 0;
    }
    ul, ol {
        margin: 8px 0 8px 20px;
        padding: 0;
    }
    li {
        margin-bottom: 4px;
    }
    code {
        background: #f0f4f8;
        padding: 2px 5px;
        border-radius: 3px;
        font-family: Consolas, monospace;
        font-size: 9.5pt;
        color: #0a3d62;
    }
    em {
        color: #555;
    }
    strong {
        color: #003366;
    }
    hr {
        border: none;
        border-top: 1px solid #dde3ed;
        margin: 20px 0;
    }
    blockquote {
        border-left: 4px solid #FFCC00;
        margin: 10px 0;
        padding: 6px 12px;
        color: #444;
        background: #fffde7;
    }
""")

full_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>{html_body}</body>
</html>
"""

html_doc = HTML(string=full_html, base_url=".")
html_doc.write_pdf(pdf_path, stylesheets=[css])

print(f"PDF created: {pdf_path}")
