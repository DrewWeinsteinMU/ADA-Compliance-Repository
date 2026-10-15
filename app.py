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
from review import manifest, apply_review

RESULTS = {}
LOCK = threading.Lock()
TTL = 1800
APP_VERSION = 'guided-review-2'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Avoid recording filenames or download tokens.

    def send(self, status, body, content_type, filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(body)

    def error(self, message, status=400):
        self.send(status, json.dumps({'error': message}).encode(), 'application/json')

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health':
            return self.send(200,json.dumps({'status':'ok','version':APP_VERSION,'review_supported':True}).encode(),'application/json')
        if path == '/':
            return self.send(200, Path(__file__).with_name('templates').joinpath('index.html').read_bytes(), 'text/html; charset=utf-8')
        parts = path.strip('/').split('/')
        if len(parts)==2 and parts[0]=='review':
            with LOCK: item=RESULTS.get(parts[1])
            if item and time.time()-item[0]<TTL:
                return self.send(200,json.dumps(manifest(item[1]['document'])).encode(),'application/json')
            return self.error('Review expired. Upload the document again.',404)
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
        if self.path not in ('/convert','/revise'):
            return self.error('Not found.', 404)
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.error('Upload from this app’s page.', 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_UPLOAD + 65536:
                return self.error('Please upload a .docx or .pdf document smaller than 15 MB.', 413)
            if self.path=='/revise':
                if length>1024*1024: return self.error('Review is too large.',413)
                request=json.loads(self.rfile.read(length))
                if not isinstance(request,dict):return self.error('Invalid review.')
                token=request.get('token')
                with LOCK: item=RESULTS.get(token) if isinstance(token,str) else None
                if not item or time.time()-item[0]>=TTL:return self.error('Review expired. Upload again.',404)
                word,changes=apply_review(item[1]['document'],request.get('edits',{}))
                outputs=process_document(word,'reviewed.docx',False,False,bool(request.get('pdf')),bool(request.get('contrast',True)),bool(request.get('enlarge',True)))
                outputs['report'] += ('\nEMPLOYEE-CONFIRMED CHANGES\n'+'\n'.join(changes)).encode()
                new_token=secrets.token_urlsafe(24)
                with LOCK:
                    if len(RESULTS)>=20:del RESULTS[min(RESULTS,key=lambda k:RESULTS[k][0])]
                    RESULTS[new_token]=(time.time(),outputs)
                return self.send(200,json.dumps({'token':new_token,'report':outputs['report'].decode(),'pdf_available':'pdf' in outputs,'review_supported':True,'version':APP_VERSION}).encode(),'application/json')
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
            outputs = process_document(uploaded.get_payload(decode=True), uploaded.get_filename(), 'headings' in fields, 'headers' in fields, 'pdf' in fields, 'contrast' in fields, 'enlarge' in fields)
            report = outputs['report'].decode('utf-8')
            token = secrets.token_urlsafe(24)
            with LOCK:
                for key in list(RESULTS):
                    if time.time()-RESULTS[key][0] >= TTL:
                        del RESULTS[key]
                if len(RESULTS) >= 20:
                    del RESULTS[min(RESULTS, key=lambda k: RESULTS[k][0])]
                RESULTS[token] = (time.time(), outputs)
            self.send(200, json.dumps({'token':token,'report':report,'pdf_available':'pdf' in outputs,'review_supported':True,'version':APP_VERSION}).encode(), 'application/json')
        except ValueError as exc:
            self.error(str(exc))
        except Exception:
            self.error('This document could not be processed. Try saving a fresh .docx or searchable PDF.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'Document accessibility app listening on {args.host}:{args.port}', flush=True)
    server.serve_forever()
