'''Webモジュール

T'sLove へのログインとコンテンツの取得を行う
'''

import io
import warnings
import time
import re
from typing import Optional, Callable

import requests
from PIL import Image  # type: ignore

from tslove.core.exception import RequestError, RetryCountExceededError

warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made.')

RETRY_COUNT = 10
RETRY_INTERVAL = 10
RETRY_ADDITIONAL = 5


class TsLoveWeb:
    '''T'sLove webアクセスクラス'''

    __instance = None
    __instance_initialized = False

    @classmethod
    def get_instance(cls):
        '''TsLoveWebのインスタンスを取得する'''
        if cls.__instance:
            return cls.__instance

        return cls()

    def __new__(cls, url: str = ''):  # pylint: disable=W0613
        if cls.__instance is None:
            cls.__instance = super(TsLoveWeb, cls).__new__(cls)
        return cls.__instance

    def __init__(self, url: str = 'https://tslove.net/'):
        '''
        :param url: T'sLove の起点URL
        '''
        if not self.__instance_initialized:
            self.__url = url
            self.__session = requests.Session()
            self.__session.headers.update({
                'User-Agent': 'tslove-tools written by T.Kyoko (tslove member_id=45642)'})
            self.__php_session_id: Optional[str] = None
            self.__sns_session_id: Optional[str] = None

            self.__retry_count = 0
            self.__total_retries = 0
            self.__instance_initialized = True

    def __del__(self):
        self.__session.close()

    @property
    def php_session_id(self) -> Optional[str]:
        '''PHPSESSID'''
        return self.__php_session_id

    @property
    def sns_session_id(self) -> Optional[str]:
        '''sns_session_id'''
        return self.__sns_session_id

    @property
    def total_retries(self) -> int:
        '''total_retries'''
        return self.__total_retries

    def __request(self, request: Callable, message: Callable = None) -> requests.Response:
        '''T'sLoveへリクエストを発行します

        RETRY_COUNT, RETRY_INTERVAL, RETRY_ADDITIONAL の値に従って
        再試行を行いながら T'sLove へのリクエストを発行します

        実際のリクエストは引数 request で指定します
        messageが与えられた場合、リトライの発生時にmessageの戻り値をprintします

        :param request: リクエストを発行する関数
        :param message: リトライメッセージを生成する関数
        :returns: request.Respose オブジェクト
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合

        '''
        while self.__retry_count < RETRY_COUNT:
            if self.__retry_count != 0:
                interval = RETRY_INTERVAL + (self.__retry_count - 1) * RETRY_ADDITIONAL
                if message:
                    print(message(interval))
                time.sleep(interval)
                self.__total_retries += 1
            try:
                response = request()
            except requests.RequestException as err:
                raise RequestError from err
            if response.ok:
                return response

            self.__retry_count += 1

        raise RetryCountExceededError()

    def __get(self, path: str, params: dict = None) -> requests.Response:
        '''T'sLoveからデータをGETします

        :param path: url path
        :param params: クエリパラメータ
        :returns: requests.Response オブジェクト
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        def request() -> requests.Response:
            url = self.__url + path if path else self.__url
            return self.__session.get(url, params=params, verify=False, allow_redirects=False, timeout=15)

        def message(interval: int) -> str:
            msg = 'Retry GET'
            msg += ' path:{}'.format(path) if path else ''
            if params:
                msg += ' action:{}'.format(params['a']) if 'a' in params else ''
                msg += ' file:{}'.format(params['filename']) if 'filename' in params else ''
            msg += ' after {} sec.'.format(interval)
            return msg

        return self.__request(request, message)

    def __post(self, path: str, payload: dict = None) -> requests.Response:
        '''T'sLoveへデータをPOSTします

        :param path: url path
        :param payload: POSTデータ
        :returns: requests.Response オブジェクト
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        def request() -> requests.Response:
            url = self.__url + path if path else self.__url
            return self.__session.post(url, data=payload, verify=False, allow_redirects=False, timeout=15)

        def message(interval: int) -> str:
            msg = 'Retry POST'
            msg += ' path:{}'.format(path) if path else ''
            if payload:
                msg += ' action:{}'.format(payload['a']) if 'a' in payload else ''
            msg += ' after {} sec.'.format(interval)
            return msg

        return self.__request(request, message)

    def login(self, username: Optional[str], password: Optional[str], php_session_id: Optional[str] = None) -> bool:
        '''T'sLoveへのログインをおこないます

        sns_session_idを取得できることによってログインの成功を判定します
        php_session_idが与えられた場合、ユーザ名とパスワードによる認証を
        バイパスしてsns_session_idの取得を試みます

        :param username: ユーザ名(メールアドレス)
        :param password: パスワード
        :param php_session_id: PHPSESSID
        :return: sns_session_idを取得できた場合 True
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        if php_session_id is None:
            if username and password:
                self.__php_session_id = self.__get_php_session_id(username, password)
            else:
                return False
        else:
            self.__php_session_id = php_session_id
            self.__session.cookies.set('PHPSESSID', php_session_id)

        if self.__php_session_id is None:
            return False

        self.__sns_session_id = self.__get_sns_session_id()
        if self.__sns_session_id is not None:
            return True

        return False

    def __get_php_session_id(self, username: str, password: str) -> Optional[str]:
        '''PHPSESSIDを取得します

        :param username: ユーザ名
        :param password: パスワード
        :return: PHPSESSID もしくは None
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        payload = {'username': username,
                   'password': password,
                   'm': 'pc',
                   'a': 'do_o_login',
                   'login_params': '',
                   'is_save': '1',
                   }

        self.__retry_count = 0

        while True:
            response = self.__post('', payload)

            if 'PHPSESSID' in response.cookies:
                return response.cookies['PHPSESSID']
            if response.status_code == 302:  # 認証失敗
                return None

            self.__retry_count += 1

    def __get_sns_session_id(self) -> Optional[str]:
        '''T'sLove session_id を取得します

        マイページ確認ページを取得してログアウトのリンクから session_id を取得します

        :return: session_id もしくは None
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        session_id_pattern = re.compile(r'a=do_inc_page_header_logout&amp;sessid=(?P<session_id>.+)"')

        params = {'m': 'pc',
                  'a': 'page_h_prof',
                  }
        page = self.get_page(params)

        result = session_id_pattern.search(page)
        if result:
            return result.group('session_id')

        return None

    def get_page(self, params: dict) -> str:
        '''ページを取得します

        :param params: クエリパラメータ
        :return: ページの内容
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        self.__retry_count = 0

        title_pattern = re.compile(r'<title>(?P<title>.+)</title>')
        while True:
            response = self.__get('', params)

            if not response.headers['Content-Type'].startswith('text/html'):
                self.__retry_count += 1
                continue

            result = title_pattern.search(response.text)
            if result and not result.group('title') == 'ページが表示できませんでした':
                return response.text

            self.__retry_count += 1

    def get_stylesheet(self) -> str:
        '''スタイルシートを取得します

        :return: スタイルシートの内容
        :raises RecuestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        self.__retry_count = 0

        while True:
            response = self.__get('xhtml_style.php', None)

            if response.headers['Content-Type'].startswith('text/css'):
                return response.text

            self.__retry_count += 1

    def get_image(self, path: str, params: dict = None) -> Image:
        '''画像を取得します

        画像が不正(Content-Type が text/html かつContent-Length 0)なものについては
        ダミーのイメージを生成して返却します

        :param path: url path
        :param params: クエリパラメータ
        :return: PIL Image オブジェクト
        :raises RequestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        self.__retry_count = 0

        while True:
            response = self.__get(path, params)

            if response.headers['Content-Type'].startswith('image/'):
                return Image.open(io.BytesIO(response.content))

            if response.headers['Content-Type'].startswith('text/html') and response.headers['Content-Length'] == '0':
                return Image.new("1", (1, 1), 1)

            self.__retry_count += 1

    def get_javascript(self, path: str) -> str:
        '''JavaScriptを取得します

        :param path: url path
        :return: JavaScriptファイルの内容
        :raises RequestError: requetsの処理に失敗した場合
        :raises RetryCountExceededError: リトライ回数が基準を超過した場合
        '''
        self.__retry_count = 0

        while True:
            response = self.__get(path, None)

            if response.headers['Content-Type'].startswith('text/javascript'):
                return response.text

            self.__retry_count += 1
