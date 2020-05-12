import requests
from bs4 import BeautifulSoup
import warnings
import time
import re

warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made.')


class WebUI:
    def __init__(self):
        self.url = 'https://tslove.net'
        self._retry_count = 10
        self._retry_interval = 10
        self._cookies = {}
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

        for count in range(self._retry_count, 0, -1):
            if count != self._retry_count:
                time.sleep(self._retry_interval)

            response = requests.post(self.url, data=payload, verify=False, allow_redirects=False)
            response.raise_for_status()

            if 'PHPSESSID' in response.cookies:
                return response.cookies['PHPSESSID']
            elif response.status_code == 302:
                return None

            # DB Error: connect failed ページが200を返してくる
            print('Retry do_o_login after {} sec.'.format(self._retry_interval))

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

    def get_page(self, params):
        for count in range(self._retry_count, 0, -1):
            if count != self._retry_count:
                time.sleep(self._retry_interval)

            response = requests.get(self.url, params=params, cookies=self._cookies, verify=False)
            response.raise_for_status()

            title_pattern = re.compile(r'<title>(?P<title>.+)</title>')
            result = title_pattern.search(response.text)
            if result and result.group('title') == 'ページが表示できませんでした':
                print('Retry {} after {} sec.'.format(params['a'], self._retry_interval))
                continue

            return response.text

        else:
            raise RuntimeError('retry counter expiered')

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
        return self.get_page(params)
