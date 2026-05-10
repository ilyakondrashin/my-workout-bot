from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

port = int(os.environ.get('PORT', 8080))
print(f"Сервер запущен на порту {port}")
HTTPServer(('0.0.0.0', port), Handler).serve_forever()
