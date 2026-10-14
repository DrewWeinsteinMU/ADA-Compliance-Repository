"""Create a genuinely tagged PDF using LibreOffice's PDF/UA export filter."""
import json
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader


def export_tagged_pdf(word):
    engine = shutil.which('soffice') or shutil.which('libreoffice')
    if not engine:
        raise ValueError('Tagged PDF export requires LibreOffice. Install LibreOffice and ensure soffice is on PATH.')
    with tempfile.TemporaryDirectory(prefix='accessible-export-') as folder:
        root = Path(folder)
        source = root / 'Accessible_Document.docx'; source.write_bytes(word)
        profile = (root / 'profile').as_uri()
        options = json.dumps({
            'PDFUACompliance': {'type': 'boolean', 'value': 'true'},
            'UseTaggedPDF': {'type': 'boolean', 'value': 'true'},
            'ExportBookmarks': {'type': 'boolean', 'value': 'true'},
        })
        try:
            process = subprocess.run([engine, '-env:UserInstallation='+profile,
                '--headless', '--convert-to', 'pdf:writer_pdf_Export:'+options,
                '--outdir', str(root), str(source)], capture_output=True, timeout=90)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('PDF export exceeded 90 seconds. Try a smaller document.') from exc
        output = root / 'Accessible_Document.pdf'
        if process.returncode or not output.exists():
            raise ValueError('LibreOffice could not export this document. Review or simplify the Word copy and try again.')
        data = output.read_bytes()
        reader = PdfReader(BytesIO(data))
        catalog = reader.trailer['/Root']
        marked = catalog.get('/MarkInfo')
        if not catalog.get('/StructTreeRoot') or not marked or not marked.get_object().get('/Marked'):
            raise ValueError('PDF export did not produce a marked structure tree. No PDF download was created.')
        return data
