"""
=============================================================================
Washer PdM SideProject: Hackathon Markdown to PDF Exporter
=============================================================================
Converts Hackathon documentation Markdown (.md) files into clean, professional
A4 printable PDFs using Python-Markdown and Microsoft Edge in headless mode.

Target Documents:
1. SCRIPT_READ_ALOUD.md -> SCRIPT_READ_ALOUD.pdf
2. VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md -> VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.pdf
3. SDP_HACKATHON_BRIEFING_SUMMARY.md -> SDP_HACKATHON_BRIEFING_SUMMARY.pdf

Design Requirements:
- Uses `markdown` package with `tables` and `fenced_code` extensions.
- Wraps output in a clean, legible print stylesheet (A4, table borders,
  no-page-break inside table rows, readable typography).
- Temporary HTML files are written to system temp directory (never into Hackathon/).
- Uses Microsoft Edge headless (--headless=new, --no-pdf-header-footer).
=============================================================================
"""

import os
import sys
import tempfile
import subprocess
import re
import markdown

# ---------------------------------------------------------------------------
# Section 1: Configuration & File Targets
# ---------------------------------------------------------------------------

TARGET_FILES = [
    "SCRIPT_READ_ALOUD.md",
    "VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md",
    "SDP_HACKATHON_BRIEFING_SUMMARY.md"
]

def find_edge_path():
    """
    Locates the Microsoft Edge executable on standard Windows paths.
    Returns the absolute path if found, or None otherwise.
    """
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

# ---------------------------------------------------------------------------
# Section 2: Print Stylesheet Template
# ---------------------------------------------------------------------------

def build_html_document(title, body_html):
    """
    Wraps generated HTML body into a complete HTML document with an A4 print stylesheet.
    Prevents table row splitting across page breaks and prevents right-edge clipping.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{
    size: A4;
    margin: 12mm 14mm 14mm 14mm;
  }}
  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.45;
    font-size: 9pt;
    margin: 0;
    padding: 0;
  }}
  h1 {{
    font-size: 16pt;
    margin-top: 0;
    margin-bottom: 8px;
    color: #0f172a;
    border-bottom: 2px solid #cbd5e1;
    padding-bottom: 4px;
    page-break-after: avoid;
  }}
  h2 {{
    font-size: 12.5pt;
    margin-top: 16px;
    margin-bottom: 6px;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 3px;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 10.5pt;
    margin-top: 12px;
    margin-bottom: 4px;
    color: #1e293b;
    page-break-after: avoid;
  }}
  p {{
    margin: 6px 0;
  }}
  ul, ol {{
    margin: 6px 0 8px 20px;
    padding: 0;
  }}
  li {{
    margin-bottom: 3px;
  }}
  blockquote {{
    border-left: 3.5px solid #0284c7;
    background-color: #f8fafc;
    margin: 8px 0;
    padding: 6px 12px;
    color: #334155;
    font-size: 8.5pt;
    border-radius: 0 4px 4px 0;
  }}
  table {{
    width: 100%;
    max-width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 8pt;
    page-break-inside: auto;
    table-layout: auto;
  }}
  tr {{
    page-break-inside: avoid;
    page-break-after: auto;
  }}
  th, td {{
    border: 1px solid #cbd5e1;
    padding: 5px 7px;
    text-align: left;
    vertical-align: top;
    word-break: break-word;
    overflow-wrap: break-word;
  }}
  th {{
    background-color: #f1f5f9;
    font-weight: 600;
    color: #0f172a;
  }}
  tr:nth-child(even) td {{
    background-color: #f8fafc;
  }}
  code {{
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
    font-size: 8pt;
    background-color: #f1f5f9;
    padding: 1.5px 3.5px;
    border-radius: 3px;
    color: #0f172a;
  }}
  pre {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 8px 10px;
    overflow-x: auto;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    font-size: 7.5pt;
    line-height: 1.35;
    page-break-inside: avoid;
    white-space: pre-wrap;
    word-break: break-all;
  }}
  pre code {{
    background: none;
    padding: 0;
  }}
  hr {{
    border: 0;
    border-top: 1px solid #e2e8f0;
    margin: 12px 0;
  }}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Section 3: Conversion & Export Logic
# ---------------------------------------------------------------------------

def convert_md_to_pdf(md_path, pdf_path, edge_path, temp_dir):
    """
    Reads a Markdown file, converts it to styled HTML, and invokes Edge headless
    to produce the target PDF file.
    """
    doc_name = os.path.basename(md_path)
    print(f"\n--- Processing: {doc_name} ---")

    # Read Markdown source
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Convert Markdown to HTML with table and fenced code extensions
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br"]
    )

    # Wrap in complete HTML print document
    title = os.path.splitext(doc_name)[0].replace("_", " ")
    full_html = build_html_document(title, html_body)

    # Save to temporary HTML file
    temp_html_path = os.path.join(temp_dir, f"{os.path.splitext(doc_name)[0]}.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    # Invoke Microsoft Edge headless to generate PDF
    cmd = [
        edge_path,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        temp_html_path
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024.0
        # Count pages from PDF bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        page_count = len(re.findall(rb'/Type\s*/Page\b', pdf_bytes))
        print(f"SUCCESS: {os.path.basename(pdf_path)} generated ({size_kb:.1f} KB, {page_count} pages)")
        return page_count
    else:
        print(f"ERROR: Failed to generate {pdf_path}")
        if res.stderr:
            print(f"Edge stderr: {res.stderr}")
        return None

# ---------------------------------------------------------------------------
# Section 4: Main Entrypoint
# ---------------------------------------------------------------------------

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    edge_path = find_edge_path()

    if not edge_path:
        print("ERROR: Microsoft Edge executable not found. Cannot generate PDFs.")
        sys.exit(1)

    print(f"Using Microsoft Edge: {edge_path}")

    # Create temporary directory for intermediate HTML files
    temp_dir = os.path.join(tempfile.gettempdir(), "pdm_hackathon_export")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Using temporary directory for HTML: {temp_dir}")

    results = {}
    for filename in TARGET_FILES:
        md_path = os.path.join(base_dir, filename)
        pdf_path = os.path.join(base_dir, os.path.splitext(filename)[0] + ".pdf")

        if not os.path.exists(md_path):
            print(f"WARNING: Source markdown file not found: {md_path}")
            continue

        pages = convert_md_to_pdf(md_path, pdf_path, edge_path, temp_dir)
        results[filename] = pages

    print("\n=============================================================================")
    print("Export Summary:")
    for filename, pages in results.items():
        pdf_name = os.path.splitext(filename)[0] + ".pdf"
        status = f"{pages} pages" if pages is not None else "FAILED"
        print(f"  - {pdf_name}: {status}")
    print("=============================================================================")

if __name__ == "__main__":
    main()
