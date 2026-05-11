from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.request
import urllib.error
import traceback

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
            print(f"[API] Получен запрос, ключ: {ANTHROPIC_API_KEY[:10]}...")
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            prompt = (
                'Определи что за еда на фото. Оцени примерный объём порции по размеру тарелки/посуды '
                'и рассчитай КБЖУ для этой порции. '
                'Ответь ТОЛЬКО в формате JSON без markdown: '
                '{"dish":"название блюда на русском","ingredients":["ингредиент1","ингредиент2"],'
                '"status":"ok/warn/bad","reason":"краткое объяснение по FODMAP",'
                '"volume":"примерный объём например 200г","kcal":350,"protein":25,"fat":12,"carbs":40} '
                'Правила FODMAP: запрещены яйца, молочное, глютен, лук, чеснок, бобовые, сахар, алкоголь. '
                'Разрешены: мясо, рыба, гречка, рис, киноа, большинство овощей, зелень. '
                'Ограничены (warn): брокколи макс 0.5 чашки, батат макс 0.5 чашки, авокадо макс 0.25 шт, клубника, малина.'
            )

            payload = json.dumps({
                'model': 'claude-sonnet-4-5',
                'max_tokens': 600,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': data['mediaType'],
                                'data': data['imageData']
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
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

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())

            print(f"[API] Успешно!")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"[API] HTTP Error {e.code}: {error_body}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'HTTP {e.code}: {error_body}'}).encode('utf-8'))

        except Exception as e:
            print(f"[API] Ошибка: {traceback.format_exc()}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

port = int(os.environ.get('PORT', 8080))
print(f'Сервер запущен на порту {port}')
print(f'API ключ установлен: {"Да" if ANTHROPIC_API_KEY else "НЕТ!"}')
HTTPServer(('0.0.0.0', port), Handler).serve_forever()
