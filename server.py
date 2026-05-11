from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.request

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/webapp.html'
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/analyze':
            self.handle_analyze()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_analyze(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            payload = json.dumps({
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 500,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'image', 'source': {'type': 'base64', 'media_type': data['mediaType'], 'data': data['imageData']}},
                        {'type': 'text', 'text': 'Определи что за еда на фото. Ответь ТОЛЬКО в формате JSON без markdown: {"dish":"название блюда на русском","ingredients":["ингредиент1","ингредиент2"],"status":"ok/warn/bad","reason":"краткое объяснение по FODMAP"} Правила FODMAP: запрещены яйца, молочное, глютен, лук, чеснок, бобовые, сахар. Разрешены: мясо, рыба, гречка, рис, киноа, большинство овощей.'}
                    ]
                }]
            }).encode('utf-8')
            req = urllib.request.Request(
                'https://api.anthropic.com/v1/messages',
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': ANTHROPIC_API_KEY,
                    'anthropic-version': '2023-06-01'
                },
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        pass

port = int(os.environ.get('PORT', 8080))
print(f'Сервер запущен на порту {port}')
HTTPServer(('0.0.0.0', port), Handler).serve_forever()
