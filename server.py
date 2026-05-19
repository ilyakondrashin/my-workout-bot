from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.request
import urllib.error
import traceback
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OURA_TOKEN = os.environ.get('OURA_TOKEN', '')

def oura_get(endpoint, start_date, end_date):
    url = f'https://api.ouraring.com/v2/usercollection/{endpoint}?start_date={start_date}&end_date={end_date}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {OURA_TOKEN}'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    return data.get('data', [])

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/webapp.html'
        elif self.path.startswith('/api/oura'):
            self.handle_oura()
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

    def handle_oura(self):
        try:
            if not OURA_TOKEN:
                self.send_json({'error': 'OURA_TOKEN не настроен'})
                return

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            result = {}

            # Sleep
            try:
                result['sleep'] = oura_get('sleep', start_date, end_date)
                result['daily_sleep'] = oura_get('daily_sleep', start_date, end_date)
                print(f"[OURA] Сон: {len(result['sleep'])} записей")
            except Exception as e:
                print(f"[OURA] Сон ошибка: {e}")
                result['sleep'] = []
                result['daily_sleep'] = []

            # Readiness
            try:
                result['readiness'] = oura_get('daily_readiness', start_date, end_date)
                print(f"[OURA] Готовность: {len(result['readiness'])} записей")
            except Exception as e:
                print(f"[OURA] Готовность ошибка: {e}")
                result['readiness'] = []

            # Activity
            try:
                result['activity'] = oura_get('daily_activity', start_date, end_date)
                print(f"[OURA] Активность: {len(result['activity'])} записей")
            except Exception as e:
                print(f"[OURA] Активность ошибка: {e}")
                result['activity'] = []

            # Stress
            try:
                result['stress'] = oura_get('daily_stress', start_date, end_date)
                print(f"[OURA] Стресс: {len(result['stress'])} записей")
            except Exception as e:
                print(f"[OURA] Стресс ошибка: {e}")
                result['stress'] = []

            # Heart rate (last 24h)
            try:
                hr_start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
                hr_url = f'https://api.ouraring.com/v2/usercollection/heartrate?start_datetime={hr_start}'
                req = urllib.request.Request(hr_url, headers={'Authorization': f'Bearer {OURA_TOKEN}'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    hr_data = json.loads(resp.read())
                result['heartrate'] = hr_data.get('data', [])[-20:]  # last 20 readings
                print(f"[OURA] ЧСС: {len(result['heartrate'])} записей")
            except Exception as e:
                print(f"[OURA] ЧСС ошибка: {e}")
                result['heartrate'] = []

            self.send_json(result)

        except Exception as e:
            print(f"[OURA] Общая ошибка: {traceback.format_exc()}")
            self.send_json({'error': str(e)})

    def handle_analyze(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            # Schedule generation request
            if data.get('schedule'):
                print(f"[SCHEDULE] Генерируем расписание...")
                payload = json.dumps({
                    'model': 'claude-sonnet-4-5',
                    'max_tokens': 1000,
                    'messages': [{'role': 'user', 'content': data['prompt']}]
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
                print(f"[SCHEDULE] Готово!")
                self.send_json(result)
                return

            print(f"[API] Запрос анализа фото...")

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
