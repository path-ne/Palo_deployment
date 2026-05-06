from http.server import HTTPServer, BaseHTTPRequestHandler
import json, requests, urllib3, hashlib, random, string

urllib3.disable_warnings()

REST_VERSION = 'v11.2'

def md5_crypt(password):
    """MD5 crypt — PAN-OS 11.x enforces phash <= 63 chars, SHA-512 exceeds that.
    MD5 crypt ($1$) produces a 34-char hash, well within the limit."""
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    try:
        import crypt
        return crypt.crypt(password, f'$1${salt}$')
    except ImportError:
        # Python 3.13+ fallback — manual MD5 crypt (RFC 2014)
        password_b = password.encode()
        salt_b     = salt.encode()

        def md5(data): return hashlib.md5(data).digest()

        # Step 1 — initial digest
        digest_b = md5(password_b + b'$1$' + salt_b + password_b)

        # Step 2 — intermediate string
        tmp = password_b + b'$1$' + salt_b
        i   = len(password_b)
        while i > 0:
            tmp += digest_b[:min(i, 16)]
            i   -= 16
        i = len(password_b)
        while i:
            tmp += b'\x00' if i & 1 else password_b[:1]
            i >>= 1
        digest_a = md5(tmp)

        # Step 3 — 1000 rounds
        for i in range(1000):
            tmp = password_b if i & 1 else digest_a
            if i % 3: tmp += salt_b
            if i % 7: tmp += password_b
            tmp += digest_a if i & 1 else password_b
            digest_a = md5(tmp)

        # Step 4 — custom base64 encoding in MD5 crypt byte order
        CHARS = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        def b64(b2, b1, b0, n):
            w = (b2 << 16) | (b1 << 8) | b0
            return ''.join(CHARS[(w >> (6*i)) & 0x3f] for i in range(n))

        c       = digest_a
        result  = b64(c[0],  c[6],  c[12], 4)
        result += b64(c[1],  c[7],  c[13], 4)
        result += b64(c[2],  c[8],  c[14], 4)
        result += b64(c[3],  c[9],  c[15], 4)
        result += b64(c[4],  c[10], c[5],  4)
        result += b64(0,     0,     c[11], 2)
        return f'$1${salt}${result}'


def get_api_key(fw_ip, user, password):
    url = f'https://{fw_ip}/api/?type=keygen&user={user}&password={password}'
    r   = requests.get(url, verify=False, timeout=10)
    if '<key>' not in r.text:
        raise ValueError(f'keygen failed: {r.text}')
    return r.text.split('<key>')[1].split('</key>')[0]


class Proxy(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length))

        fw_ip    = body.get('fw_ip')
        user     = body.get('user',     'local')
        password = body.get('password', 'test123!')

        # ── get API key ───────────────────────────────────────
        try:
            api_key = get_api_key(fw_ip, user, password)
        except Exception as e:
            self._respond(502, {'error': str(e)})
            return

        call_type = body.get('type', 'config')

        # ── XML API: config set ───────────────────────────────
        if call_type == 'config':
            params = {
                'type':    'config',
                'action':  body.get('action', 'set'),
                'xpath':   body.get('xpath'),
                'element': body.get('element'),
                'key':     api_key
            }
            try:
                r = requests.get(f'https://{fw_ip}/api/', params=params,
                                 verify=False, timeout=30)
                self._respond(200, {'status': 'ok', 'response': r.text})
            except Exception as e:
                self._respond(502, {'error': str(e)})

        # ── XML API: commit ───────────────────────────────────
        elif call_type == 'commit':
            params = {'type': 'commit', 'cmd': '<commit></commit>', 'key': api_key}
            try:
                r = requests.get(f'https://{fw_ip}/api/', params=params,
                                 verify=False, timeout=60)
                self._respond(200, {'status': 'ok', 'response': r.text})
            except Exception as e:
                self._respond(502, {'error': str(e)})

        # ── XML API: create user with hashed password ─────────
        elif call_type == 'create_user':
            new_user     = body.get('new_user')
            new_password = body.get('new_password')
            phash        = md5_crypt(new_password)
            params = {
                'type':    'config',
                'action':  'set',
                'xpath':   f"/config/mgt-config/users/entry[@name='{new_user}']",
                'element': (
                    f'<phash>{phash}</phash>'
                    f'<permissions><role-based><superuser>yes</superuser>'
                    f'</role-based></permissions>'
                ),
                'key': api_key
            }
            try:
                r = requests.get(f'https://{fw_ip}/api/', params=params,
                                 verify=False, timeout=30)
                self._respond(200, {'status': 'ok', 'response': r.text})
            except Exception as e:
                self._respond(502, {'error': str(e)})

        # ── XML API: keygen only (connectivity test) ──────────
        elif call_type == 'keygen':
            self._respond(200, {'status': 'ok', 'response': 'keygen success'})

        # ── REST API ──────────────────────────────────────────
        elif call_type == 'rest':
            method   = body.get('method',   'POST').upper()
            endpoint = body.get('endpoint', '')
            payload  = body.get('payload',  {})
            url      = f'https://{fw_ip}{endpoint}'
            headers  = {
                'X-PAN-KEY':    api_key,
                'Content-Type': 'application/json'
            }
            try:
                r = requests.request(
                    method, url,
                    headers=headers,
                    json=payload,
                    verify=False,
                    timeout=30
                )
                self._respond(200, {'status': 'ok', 'response': r.text,
                                    'http_code': r.status_code})
            except Exception as e:
                self._respond(502, {'error': str(e)})

        else:
            self._respond(400, {'error': f'unknown type: {call_type}'})

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type',   'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f'[proxy] {self.address_string()} — {fmt % args}')


if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), Proxy)
    print(f'[proxy] PAN-OS {REST_VERSION} | running on http://localhost:8080 — Ctrl+C to stop')
    server.serve_forever()
