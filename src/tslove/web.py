import requests
from bs4 import BeautifulSoup
from PIL import Image
import io
import warnings
import time
import re

warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made.')


class WebUI:
    def __init__(self, url='https://tslove.net/'):
        self.url = url
        self._retry_count = 10
        self._retry_interval = 10
        self._retry_additional = 5
        self._cookies = {}
        self.last_retries = 0
        self._request_header = {
            'User-Agent': 'tslove-tools written by T.Kyoko (tslove member_id=45642)',
        }
        self._sns_session_id = None

    def login(self, username, password, php_session_id=None):
        if php_session_id is None:
            self._cookies['PHPSESSID'] = self._get_php_session_id(username, password)
        else:
            self._cookies['PHPSESSID'] = php_session_id

        self._sns_session_id = self._get_sns_session_id()
        if self._sns_session_id is not None:
            return True
        else:
            return False

    def _get_php_session_id(self, username, password):
        payload = {'username': username,
                   'password': password,
                   'm': 'pc',
                   'a': 'do_o_login',
                   'login_params': '',
                   'is_save': '1',
                   }

        for count in range(self._retry_count):
            if count != 0:
                interval = self._retry_interval + (count - 1) * self._retry_additional
                print('Retry do_o_login after {} sec.'.format(interval))
                time.sleep(interval)

            response = requests.post(self.url, headers=self._request_header, data=payload, verify=False, allow_redirects=False, timeout=15)
            response.raise_for_status()

            if 'PHPSESSID' in response.cookies:
                self.last_retries += count
                return response.cookies['PHPSESSID']
            elif response.status_code == 302:
                self.last_retries += count
                return None

            # DB Error: connect failed ページが200を返してくる

        else:
            raise RuntimeError('retry counter expiered')

    def _get_sns_session_id(self):
        pattern = re.compile(r'\./\?m=pc&a=do_inc_page_header_logout&sessid=(?P<session_id>.+)')

        soup = BeautifulSoup(self.get_myprofile_page(), 'html.parser')
        logout_label = soup.find('li', id='globalNav_9')
        if logout_label is None:
            return None

        result = pattern.match(logout_label.a['href'])
        if result:
            return result.group('session_id')
        else:
            return None

    def get_contents(self, path='', params={}, cond=None):
        for count in range(self._retry_count):
            if count != 0:
                interval = self._retry_interval + (count - 1) * self._retry_additional
                msg = 'Retry'
                msg += ' path:{}'.format(path) if path else ''
                msg += ' action:{}'.format(params['a']) if 'a' in params else ''
                msg += ' file:{}'.format(params['filename']) if 'filename' in params else ''
                msg += ' after {} sec.'.format(interval)
                print(msg)
                time.sleep(interval)

            response = requests.get(self.url + path, headers=self._request_header, params=params, cookies=self._cookies, verify=False, timeout=15)
            response.raise_for_status()

            if cond is None or cond(response):
                self.last_retries += count
                return response
        else:
            raise RuntimeError('retry counter expiered')

    def get_page(self, params):
        def cond(response):
            title_pattern = re.compile(r'<title>(?P<title>.+)</title>')
            result = title_pattern.search(response.text)
            return result and not result.group('title') == 'ページが表示できませんでした'

        response = self.get_contents(params=params, cond=cond)
        return response.text

    def get_stylesheet(self):
        def cond(response):
            response.encoding = response.apparent_encoding

            pattern = re.compile(r'body, div, p, pre, blockquote, th, td,')
            return pattern.search(response.text)

        response = self.get_contents(path='xhtml_style.php')
        return response.text

    def get_image(self, path, params=None):
        def cond(response):
            return response.headers['Content-Type'].startswith('image/') or\
                (response.headers['Content-Type'] == 'text/html' and response.headers['Content-Length'] == '0')

        response = self.get_contents(path, params, cond)
        if response.headers['Content-Type'].startswith('image/'):
            return Image.open(io.BytesIO(response.content))
        else:
            return Image.new("1", (1, 1), 1)

    def get_myprofile_page(self):
        params = {'m': 'pc',
                  'a': 'page_h_prof',
                  }
        return self.get_page(params)

    def get_diary_page(self, diary_id):
        params = {'m': 'pc',
                  'a': 'page_fh_diary',
                  'target_c_diary_id': diary_id,
                  'order': 'asc',
                  'page_size': 100
                  }
        page = self.get_page(params)

        error_pattern = re.compile(r'<td>該当する日記が見つかりません。</td>')
        if error_pattern.search(page):
            raise RuntimeError('No such diary')

        return page
