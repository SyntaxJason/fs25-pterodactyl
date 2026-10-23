"""Drive the GIANTS portal with cookies, bounded requests and HTML entity decoding."""
import http.client
import http.cookies
import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlparse


class Form(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}
        self.buttons = set()
        self.select = None
        self.first = None
        self.chosen = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        name = a.get('name')
        if tag == 'input' and name:
            kind = a.get('type', 'text').lower()
            if kind in ('button', 'submit'):
                self.buttons.add(name)
            elif kind == 'checkbox':
                self.values[name] = a.get('value', 'on') if 'checked' in a else 'off'
            elif kind != 'radio' or 'checked' in a:
                self.values[name] = a.get('value', '')
        elif tag == 'button' and name:
            self.buttons.add(name)
        elif tag == 'select' and name:
            self.select, self.first, self.chosen = name, None, None
        elif tag == 'option' and self.select:
            value = a.get('value', '')
            if self.first is None:
                self.first = value
            if 'selected' in a:
                self.chosen = value

    def handle_endtag(self, tag):
        if tag == 'select' and self.select:
            self.values[self.select] = self.chosen if self.chosen is not None else self.first or ''
            self.select = None


class Text(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.hidden = False
        self.lines = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = False

    def handle_data(self, value):
        if not self.hidden and value.strip():
            self.lines.append(value.strip())


class Portal:
    def __init__(self, host, port, username, password):
        self.host, self.port = host, int(port)
        self.username, self.password = username, password
        self.cookie = ''

    def request(self, data=None, _path='/index.html?lang=en', _redirects=0):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=8)
        headers = {'Connection': 'close', 'User-Agent': 'fs25-ptero/1.0'}
        if self.cookie:
            headers['Cookie'] = self.cookie
        body = urlencode(data).encode() if data is not None else None
        if body is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            conn.request('POST' if body is not None else 'GET', _path, body, headers)
            res = conn.getresponse()
            text = res.read().decode('utf-8', errors='replace')
            if not 200 <= res.status < 400:
                raise RuntimeError(f'GIANTS portal HTTP {res.status}')
            for name, value in res.getheaders():
                if name.lower() == 'set-cookie':
                    cookies = http.cookies.SimpleCookie()
                    cookies.load(value)
                    if 'SessionID' in cookies:
                        self.cookie = 'SessionID=' + cookies['SessionID'].value
            location = res.getheader('Location')
            if res.status in (301, 302, 303, 307, 308) and location:
                if _redirects >= 5:
                    raise RuntimeError('Too many GIANTS portal redirects.')
                target = urlparse(urljoin(f'http://{self.host}:{self.port}{_path}', location))
                if target.scheme != 'http' or target.hostname != self.host or (target.port or 80) != self.port:
                    raise RuntimeError('Unexpected external GIANTS portal redirect.')
                conn.close()
                path = target.path + ('?' + target.query if target.query else '')
                return self.request(data if res.status in (307, 308) else None, path, _redirects + 1)
            return text
        finally:
            conn.close()

    def login(self):
        self.request({'username': self.username, 'password': self.password, 'login': 'Login'})
        if not self.cookie:
            raise RuntimeError('GIANTS login failed: no session cookie. Check WEB_USERNAME/WEB_PASSWORD.')

    def form(self):
        form = Form()
        form.feed(self.request())
        return form

    def start(self):
        self.login()
        html = self.request()
        form = Form()
        form.feed(html)
        if 'stop_server' in form.buttons:
            return
        expected = {'game_name', 'admin_password', 'game_password', 'savegame', 'server_port', 'max_player'}
        if not expected.issubset(form.values):
            raise RuntimeError('GIANTS settings form missing; login or portal layout changed.')
        response = self.request({**form.values, 'start_server': 'Start'})
        previous = set(Text(html).lines)
        for message in Text(response).lines:
            if message not in previous and re.search(r'too long|too short|invalid|failed|error|not allowed|is required', message, re.I):
                raise RuntimeError('GIANTS rejected the game session: ' + message)

    def stop(self):
        self.login()
        self.request({'stop_server': 'Stop'})
