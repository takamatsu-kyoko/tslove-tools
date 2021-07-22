'''Webモジュール

T'sLove へのログインとコンテンツの取得を行う
'''

import io
import warnings
import time
import re
from typing import Optional, Callable

import requests
from bs4 import BeautifulSoup  # type: ignore
from PIL import Image  # type: ignore

warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made.')

RETRY_COUNT = 10
RETRY_INTERVAL = 10
RETRY_ADDITIONAL = 5


class WebUI:
    '''T'sLove webアクセスクラス'''

    def __init__(self, url: str = 'https://tslove.net/'):
        '''
        :param url: T'sLove の起点URL
        '''
        self.url = url
        self._cookies: dict = {}
        self.last_retries = 0
        self._request_header = {
            'User-Agent': 'tslove-tools written by T.Kyoko (tslove member_id=45642)',
        }
        self._sns_session_id: Optional[str] = None

    def login(self, username: str, password: str, php_session_id: str = None) -> bool:
        '''T'sLoveへのログインをおこないます

        sns_session_idを取得できることによってログインの成功を判定します
        php_session_idが与えられた場合、ユーザ名とパスワードによる認証を
        バイパスしてsns_session_idの取得を試みます

        :param username: ユーザ名(メールアドレス)
        :param password: パスワード
        :param php_session_id: PHPSESSID
        :return: sns_session_idを取得できた場合 True
        '''
        if php_session_id is None:
            self._cookies['PHPSESSID'] = self._get_php_session_id(username, password)
        else:
            self._cookies['PHPSESSID'] = php_session_id

        self._sns_session_id = self._get_sns_session_id()

        if self._sns_session_id is not None:
            return True

        return False

    def _get_php_session_id(self, username: str, password: str) -> Optional[str]:
        '''PHPSESSIDを取得します

        :param username: ユーザ名
        :param password: パスワード
        :return: PHPSESSID もしくは None
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        payload = {'username': username,
                   'password': password,
                   'm': 'pc',
                   'a': 'do_o_login',
                   'login_params': '',
                   'is_save': '1',
                   }

        for count in range(RETRY_COUNT):
            if count != 0:
                interval = RETRY_INTERVAL + (count - 1) * RETRY_ADDITIONAL
                print('Retry do_o_login after {} sec.'.format(interval))
                time.sleep(interval)

            response = requests.post(self.url, headers=self._request_header, data=payload, verify=False, allow_redirects=False, timeout=15)
            response.raise_for_status()

            if 'PHPSESSID' in response.cookies:
                self.last_retries += count
                return response.cookies['PHPSESSID']
            if response.status_code == 302:
                self.last_retries += count
                return None

            # DB Error: connect failed ページが200を返してくる

        raise RuntimeError('retry counter expiered')

    def _get_sns_session_id(self) -> Optional[str]:
        '''T'sLove session_id を取得します

        マイページ確認ページを取得してログアウトのリンクから session_id を取得します

        :return: session_id もしくは None
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        pattern = re.compile(r'\./\?m=pc&a=do_inc_page_header_logout&sessid=(?P<session_id>.+)')

        soup = BeautifulSoup(self.get_myprofile_page(), 'html.parser')
        logout_label = soup.find('li', id='globalNav_9')
        if logout_label is None:
            return None

        result = pattern.match(logout_label.a['href'])
        if result:
            return result.group('session_id')

        return None

    def get_contents(self, path: str = '', params: dict = None, cond: Callable = None) -> requests.Response:
        '''コンテンツを取得します

        :param path: url path
        :param params: クエリパラメータ
        :param cond: コンテンツの取得確認関数
        :return: requests Respose オブジェクト
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        if params is None:
            params = {}
        for count in range(RETRY_COUNT):
            if count != 0:
                interval = RETRY_INTERVAL + (count - 1) * RETRY_ADDITIONAL
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

        raise RuntimeError('retry counter expiered')

    def get_page(self, params: dict) -> str:
        '''ページを取得します

        :param params: クエリパラメータ
        :return: ページの内容
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        def cond(response):
            title_pattern = re.compile(r'<title>(?P<title>.+)</title>')
            result = title_pattern.search(response.text)
            return result and not result.group('title') == 'ページが表示できませんでした'

        response = self.get_contents(params=params, cond=cond)
        return response.text

    def get_stylesheet(self) -> str:
        '''スタイルシートを取得します

        :return: スタイルシートの内容
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        def cond(response):
            response.encoding = response.apparent_encoding

            pattern = re.compile(r'body, div, p, pre, blockquote, th, td,')
            return pattern.search(response.text)

        response = self.get_contents(path='xhtml_style.php', cond=cond)
        return response.text

    def get_image(self, path: str, params: dict = None) -> Image:
        '''画像を取得します

        画像が不正(Content-Type が text/html かつContent-Length 0)なものについては
        ダミーのイメージを生成して返却します

        :param path: url path
        :param params: クエリパラメータ
        :return: PIL Image オブジェクト
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        def cond(response):
            return response.headers['Content-Type'].startswith('image/') or\
                (response.headers['Content-Type'] == 'text/html' and response.headers['Content-Length'] == '0')

        response = self.get_contents(path, params, cond)
        if response.headers['Content-Type'].startswith('image/'):
            return Image.open(io.BytesIO(response.content))

        return Image.new("1", (1, 1), 1)

    def get_javascript(self, path: str) -> str:
        '''JavaScriptを取得します

        :param path: url path
        :return: JavaScriptファイルの内容
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''

        def cond(response):
            return response.headers['Content-Type'] == 'text/javascript'

        response = self.get_contents(path, cond=cond)
        return response.text

    def get_myprofile_page(self) -> str:
        '''マイページ確認ページを取得します

        :return: ページの内容
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        '''
        params = {'m': 'pc',
                  'a': 'page_h_prof',
                  }
        return self.get_page(params)

    def get_diary_page(self, diary_id: str) -> str:
        '''日記を取得します

        :param diary_id: diary_id
        :return: 日記の内容
        :raises RuntimeErorr: リトライ回数が基準を超過した場合
        :raises RuntimeErorr: 指定したdiary_idの日記が見つからなかった場合
        '''
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
