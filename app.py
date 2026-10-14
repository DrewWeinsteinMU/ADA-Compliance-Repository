"""Local upload application. Run behind an authenticated HTTPS gateway for shared use."""
import argparse
import json
import secrets
import threading
import time
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from converter import MAX_UPLOAD
from documents import process_document

RESULTS = {}
LOCK = threading.Lock()
TTL = 1800

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Avoid recording filenames or download tokens.

    def send(self, status, body, content_type, filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(body)

    def error(self, message, status=400):
        self.send(status, json.dumps({'error': message}).encode(), 'application/json')

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            return self.send(200, Path(__file__).with_name('templates').joinpath('index.html').read_bytes(), 'text/html; charset=utf-8')
        parts = path.strip('/').split('/')
        if len(parts) == 3 and parts[0] == 'download':
            with LOCK:
                item = RESULTS.get(parts[1])
            if item and time.time() - item[0] < TTL:
                formats = {
                    'document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Accessible_Document.docx'),
                    'html': ('text/html; charset=utf-8', 'Document_Text.html'),
                    'pdf': ('application/pdf', 'Accessible_Document.pdf'),
                    'report': ('text/plain; charset=utf-8', 'Accessibility_Review.txt'),
                }
                if parts[2] in formats and parts[2] in item[1]:
                    mime, filename = formats[parts[2]]
                    return self.send(200, item[1][parts[2]], mime, filename)
        self.error('This download has expired or does not exist. Upload the document again.', 404)

    def do_POST(self):
        if self.path != '/convert':
            return self.error('Not found.', 404)
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.error('Upload from this app’s page.', 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_UPLOAD + 65536:
                return self.error('Please upload a .docx or .pdf document smaller than 15 MB.', 413)
            ctype = self.headers.get('Content-Type', '')
            if not ctype.startswith('multipart/form-data') or '\r' in ctype or '\n' in ctype:
                return self.error('Use the document upload form.')
            message = BytesParser(policy=default).parsebytes(('Content-Type: '+ctype+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+self.rfile.read(length))
            fields = {}
            for part in message.iter_parts():
                fields[part.get_param('name', header='content-disposition')] = part
            uploaded = fields.get('document')
            if uploaded is None or not (uploaded.get_filename() or '').lower().endswith(('.docx', '.pdf')):
                return self.error('Choose a .docx or .pdf file. Save older .doc files as .docx in Word first.')
            outputs = process_document(uploaded.get_payload(decode=True), uploaded.get_filename(), 'headings' in fields, 'headers' in fields, 'pdf' in fields, 'contrast' in fields)
            report = outputs['report'].decode('utf-8')
            token = secrets.token_urlsafe(24)
            with LOCK:
                for key in list(RESULTS):
                    if time.time()-RESULTS[key][0] >= TTL:
                        del RESULTS[key]
                if len(RESULTS) >= 20:
                    del RESULTS[min(RESULTS, key=lambda k: RESULTS[k][0])]
                RESULTS[token] = (time.time(), outputs)
            self.send(200, json.dumps({'token':token,'report':report,'pdf_available':'pdf' in outputs}).encode(), 'application/json')
        except ValueError as exc:
            self.error(str(exc))
        except Exception:
            self.error('This document could not be processed. Try saving a fresh .docx or searchable PDF.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    args = parser.parse_args()
    print(f'Document accessibility app listening on {args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
