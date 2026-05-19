from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.request
import urllib.error
import traceback
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OURA_TOKEN = os.environ.get('OURA_TOKEN', '')

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/webapp.html'
        elif self.path.startswith('/api/sleep'):
            self.handle_sleep()
            return
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

    def handle_sleep(self):
        try:
            if not OURA_TOKEN:
                self.send_json({'error': 'OURA_TOKEN не настроен'})
                return

            # Get last 7 days
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            # Fetch sleep data
            sleep_url = f'https://api.ouraring.com/v2/usercollection/sleep?start_date={start_date}&end_date={end_date}'
            req = urllib.request.Request(
                sleep_url,
                headers={'Authorization': f'Bearer {OURA_TOKEN}'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                sleep_data = json.loads(resp.read())

            # Fetch daily sleep scores
            score_url = f'https://api.ouraring.com/v2/usercollection/daily_sleep?start_date={start_date}&end_date={end_date}'
            req2 = urllib.request.Request(
                score_url,
                headers={'Authorization': f'Bearer {OURA_TOKEN}'}
            )
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                score_data = json.loads(resp2.read())

            print(f"[OURA] Получено {len(sleep_data.get('data',[]))} записей сна")
            self.send_json({'sleep': sleep_data.get('data', []), 'scores': score_data.get('data', [])})

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"[OURA] Error {e.code}: {error_body}")
            self.send_json({'error': f'Oura API error {e.code}: {error_body}'})
        except Exception as e:
            print(f"[OURA] Exception: {traceback.format_exc()}")
            self.send_json({'error': str(e)})

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
                        {'type': 'image', 'source': {'type': 'base64', 'media_type': data['mediaType'], 'data': data['imageData']}},
                        {'type': 'text', 'text': prompt}
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
            self.send_json(result)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"[API] HTTP Error {e.code}: {error_body}")
            self.send_json({'error': f'HTTP {e.code}: {error_body}'}, status=500)
        except Exception as e:
            print(f"[API] Ошибка: {traceback.format_exc()}")
            self.send_json({'error': str(e)}, status=500)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]} {args[1]}")

port = int(os.environ.get('PORT', 8080))
print(f'Сервер запущен на порту {port}')
print(f'API ключ: {"Да" if ANTHROPIC_API_KEY else "НЕТ!"}')
print(f'Oura токен: {"Да" if OURA_TOKEN else "НЕТ"}')
HTTPServer(('0.0.0.0', port), Handler).serve_forever()
