"""Fetch the operator's licensed installer from the official GIANTS portal."""
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse, unquote, urljoin
from urllib.request import Request, build_opener, HTTPCookieProcessor

PORTAL = 'https://eshop.giants-software.com/downloads.php'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            url = urlparse(href)
            if url.scheme == 'https' and (url.hostname or '').endswith('.giants-software.com'):
                if url.path.lower().endswith(('_esd.img', '.zip')) and 'farmingsimulator25' in url.path.lower():
                    self.links.append(href)


class Catalog(HTMLParser):
    """Current GIANTS portal: each platform row contains a POST download form."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.row = None
        self.form = None
        self.downloads = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'tr':
            self.row = {'text': [], 'forms': []}
        elif tag == 'form' and self.row is not None:
            self.form = {'action': urljoin(PORTAL, a.get('action', '')), 'method': a.get('method', 'get').lower(), 'fields': {}}
            self.row['forms'].append(self.form)
        elif tag == 'input' and self.form is not None and a.get('name'):
            self.form['fields'][a['name']] = a.get('value', '')

    def handle_data(self, text):
        if self.row is not None:
            self.row['text'].append(text)

    def handle_endtag(self, tag):
        if tag == 'form':
            self.form = None
        elif tag == 'tr' and self.row is not None:
            text = ' '.join(self.row['text']).lower()
            if 'windows' in text and re.search(r'farming\s*simulator\s*25', text) and re.search(r'\b(img|zip)\b', text):
                for form in self.row['forms']:
                    action = urlparse(form['action'])
                    if (form['method'] == 'post' and action.scheme == 'https'
                            and action.hostname == 'eshop.giants-software.com' and action.path == '/download.php'
                            and form['fields'].get('downloadId')):
                        self.downloads.append(form)
            self.row, self.form = None, None


def installer_response(opener, key, log):
    url = os.environ.get('FS25_DOWNLOAD_URL', '').strip()
    headers = {'Referer': PORTAL, 'User-Agent': 'Mozilla/5.0 (fs25-ptero/1.1)'}
    if url:
        if urlparse(url).scheme != 'https':
            raise RuntimeError('FS25_DOWNLOAD_URL must use HTTPS.')
        return opener.open(Request(url, headers=headers), timeout=60)
    log('Requesting your installer from the GIANTS download portal.')
    # The current portal's public key form uses GET; cookie state is retained
    # when submitting its download form. Never log this URL or any form values.
    req = Request(PORTAL + '?' + urlencode({'activationKey': key}), headers=headers)
    with opener.open(req, timeout=30) as response:
        html = response.read().decode('utf-8', errors='replace')
    catalog = Catalog()
    catalog.feed(html)
    if catalog.downloads:
        form = catalog.downloads[0]
        log('Found the licensed FS25 Windows installer. Submitting GIANTS download form.')
        req = Request(form['action'], data=urlencode(form['fields']).encode(), headers=headers)
        return opener.open(req, timeout=60)
    # Keep support for the previous portal's direct official CDN links.
    links = Links()
    links.feed(html)
    if links.links:
        return opener.open(Request(links.links[0], headers=headers), timeout=60)
    raise RuntimeError('GIANTS returned no FS25 Windows download. Check FS25_PRODUCT_KEY or upload the installer to installer/.')


def download(directory, key, log):
    opener = build_opener(HTTPCookieProcessor())
    with installer_response(opener, key, log) as response:
        name = response.headers.get_filename() or unquote(urlparse(response.geturl()).path.rsplit('/', 1)[-1])
        name = Path(name.replace('\\', '/')).name
        if not name.lower().endswith(('.img', '.zip', '.exe')) or response.headers.get_content_type() == 'text/html':
            raise RuntimeError('GIANTS did not return an installer file after the download request.')
        target = directory / name
        partial = target.with_name(target.name + '.part')
        log('Downloading installer; the first start may take a while.')
        size = int(response.headers.get('Content-Length', 0))
        written, next_report = 0, 1024**3
        with partial.open('wb') as out:
            while block := response.read(4 * 1024**2):
                out.write(block)
                written += len(block)
                if written >= next_report:
                    log(f'Installer download: {written // 1024**2} MiB' + (f' / {size // 1024**2} MiB' if size else ''))
                    next_report += 1024**3
        if size and written != size:
            raise RuntimeError('Incomplete installer download; restart to retry.')
    partial.replace(target)
    return target
