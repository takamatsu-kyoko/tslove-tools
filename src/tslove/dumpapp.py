'''ダンプアプリケーションの基本的な機能を提供します'''

import getpass
import os
import re
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

    # TODO 画像の取得は取得元,保存先の対のリストを入力として共通化する
    def _fetch_images(self, image_paths: set, overwrite=False):
        '''画像を取得します

        self._config の output_path 属性を利用します

        画像の取得の失敗はメッセージの出力のみで処理を継続します。例外の送出はありません

        :param image_paths: 取得する画像のパスの集合
        :param overwrite: 画像を上書きする場合 True
        '''
        assert hasattr(self._config, 'output_path')

        output_path = self._config.output_path['image']

        for path in image_paths:
            if '://' in path:
                continue

            filename = os.path.join(output_path, self._convert_image_path_to_filename(path))
            if os.path.exists(filename) and overwrite is False:
                continue

            try:
                if 'img.php' in path:
                    params = {'m': 'pc',
                              'filename': self._convert_image_path_to_filename(path),
                              }
                    image = self._web.get_image('img.php', params)
                else:
                    image = self._web.get_image(path)
                image.save(filename)
            except (WebAccessError, OSError) as err:
                print('Can not get image {}. {}'.format(path, err))
                continue

    # TODO 画像の取得は取得元,保存先の対のリストを入力として共通化する
    # DiaryDumpApp.fix_linkが使う
    @staticmethod
    def _convert_image_path_to_filename(path: str) -> str:
        '''画像のパスをファイル名に変換します

        :param path: 変換前のpath
        :return: 変換後のpath
        '''
        pattern = re.compile(r'filename=(?P<filename>[^&;?]+)')
        result = pattern.search(path)
        if result:
            filename = result.group('filename')
        else:
            filename = os.path.basename(path)

        return filename
