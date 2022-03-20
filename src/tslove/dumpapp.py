'''ダンプアプリケーションの基本的な機能を提供します'''

import getpass
import os
from typing import Any

from tslove.core.web import TsLoveWeb
from tslove.core.exception import WebAccessError


class DumpApp():  # pylint: disable=R0903
    '''ダンプアプリケーションの基底クラス'''

    def __init__(self) -> None:
        self._config: Any = None
        self._web = TsLoveWeb(url='https://tslove.net/')
        self._page_info: dict = {}

    def _login(self) -> bool:
        '''ログイン処理を行います

        self._config の php_session_id と echo_password 属性を利用します

        :return: ログインに成功した場合 True
        '''
        assert hasattr(self._config, 'php_session_id')
        assert hasattr(self._config, 'echo_password')

        try:
            if self._config.php_session_id is not None:
                if self._web.login(None, None, self._config.php_session_id):
                    return True

            print('Enter username and password')
            username = input('user: ')
            if not self._config.echo_password:
                password = getpass.getpass(prompt='pass: ')
            else:
                password = input('pass: ')
            return self._web.login(username, password)
        except WebAccessError as err:
            print(err)
            return False

    def _prepare_directories(self) -> None:
        '''出力先のディレクトリを用意します

        self._config の output_path 属性を利用します

        :raises: OSError ディレクトリの作成に失敗した場合
        '''
        assert hasattr(self._config, 'output_path')

        directories = self._config.output_path.values()
        try:
            for directory in directories:
                if not os.path.exists(directory):
                    os.mkdir(directory)
        except OSError as err:
            print('Can not create directory. {}'.format(err))
            raise err
