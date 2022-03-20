'''ダンプアプリケーションの基本的な機能を提供します'''

import datetime
import getpass
import json
import os
import re
from typing import Any

from tslove.core.web import TsLoveWeb
from tslove.core.exception import WebAccessError


class DumpApp():  # pylint: disable=R0903
    '''ダンプアプリケーションの基底クラス'''
    STYLESHEET_URL_PATTERN = re.compile(r'url\((?P<path>.+)\)')

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

    def _dump_stylesheet(self) -> None:
        '''スタイルシートをダンプします

        self._config の output_path 属性を利用します

        :raises: WebAccessError スタイルシート本文の取得に失敗した場合
        :raises: OSError ファイルの出力に失敗した場合
        '''
        assert hasattr(self._config, 'output_path')

        stylesheet_file_name = os.path.join(self._config.output_path['stylesheet'], 'tslove.css')
        if not os.path.exists(stylesheet_file_name):
            try:
                stylesheet = self._web.get_stylesheet()
                image_paths = self.__collect_stylesheet_image_paths(stylesheet)
                self.__fetch_stylesheet_images(image_paths)
                self.__output_stylesheet(stylesheet, stylesheet_file_name)
            except (WebAccessError, OSError) as err:
                print('Can not get stylesheet. {}'.format(err))
                raise err

    # TODO この機能はStylesheetクラスを作成してそちらに移す
    @staticmethod
    def __collect_stylesheet_image_paths(stylesheet: str) -> set:
        '''スタイルシートに含まれる画像ファイルのパスを収集します

        :param stylesheet: スタイルシートの内容
        :return: 画像ファイルのパスの集合
        '''
        paths = set()
        for line in stylesheet.splitlines():
            result = DumpApp.STYLESHEET_URL_PATTERN.search(line)
            if result:
                paths.add(result.group('path'))

        return paths

    # TODO 画像の取得は取得元,保存先の対のリストを入力として共通化する
    def __fetch_stylesheet_images(self, image_paths: set, overwrite=False) -> None:
        '''スタイルシートに含まれる画像を取得します

        self._config の output_path 属性を利用します

        画像の取得の失敗はメッセージの出力のみで処理を継続します。例外の送出はありません

        :param image_paths: 取得する画像のパスの集合
        :param overwrite: 画像を上書きする場合 True
        '''
        assert hasattr(self._config, 'output_path')

        output_path = self._config.output_path['stylesheet']
        exclude_path = ['./skin/default/img/marker.gif']

        for path in image_paths:
            if path in exclude_path:
                continue

            filename = os.path.join(output_path, self.__convert_stylesheet_image_path_to_filename(path))
            if os.path.exists(filename) and overwrite is False:
                continue

            try:
                image = self._web.get_image(path)
                image.save(filename)
            except (WebAccessError, OSError) as err:
                print('Can not get stylesheets image {}. {}'.format(path, err))
                continue

    # TODO 画像の取得は取得元,保存先の対のリストを入力として共通化する
    @staticmethod
    def __convert_stylesheet_image_path_to_filename(path: str) -> str:
        '''スタイルシートに含まれる画像のパスをファイル名に変換します

        :param path: 変換前のpath
        :return: 変換後のpath
        '''
        pattern = re.compile(r'image_filename=(?P<filename>[^&;?]+)')
        result = pattern.search(path)
        if result:
            filename = result.group('filename')
        else:
            filename = os.path.basename(path)

        return filename

    def __output_stylesheet(self, stylesheet: str, file_name: str) -> None:
        '''スタイルシートをファイルに出力します

        :param stylesheet: スタイルシート本文
        :param file_name: 出力先
        :raises: OSError ファイルの書き込みに失敗した場合
        '''
        with open(file_name, 'w', encoding='utf-8') as file:
            for line in stylesheet.splitlines():
                result = DumpApp.STYLESHEET_URL_PATTERN.search(line)
                if result:
                    old_path = result.group('path')
                    new_path = './' + self.__convert_stylesheet_image_path_to_filename(old_path)
                    line = line.replace(old_path, new_path)
                file.write(line + '\n')

    def _fetch_scripts(self, script_paths: set, overwrite=False) -> None:
        '''スクリプトを取得します

        self._config の output_path 属性を利用します

        スクリプトの取得の失敗はメッセージの出力のみで処理を継続します。例外の送出はありません

        :params script_paths: 取得するスクリプトのパスの集合
        :param overwrite: スクリプトを上書きする場合 True
        '''
        assert hasattr(self._config, 'output_path')

        output_path = self._config.output_path['script']

        for path in script_paths:

            if path.startswith('./js/prototype.js') or path.startswith('./js/Selection.js') or path == './js/comment.js':
                continue

            filename = os.path.join(output_path, os.path.basename(path))
            if os.path.exists(filename) and overwrite is False:
                continue

            try:
                script = self._web.get_javascript(path)
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(script)

            except (WebAccessError, OSError) as err:
                print('Can not get script {}. {}'.format(path, err))
                continue

    def _load_page_info(self) -> None:
        '''ページ情報ファイルを読み込みます

        self._config の output_path 属性を利用します

        :raises: OSError ファイルの読み込みに失敗した場合
        '''
        assert hasattr(self._config, 'output_path')

        def convert_datetime(dct):
            if 'date' in dct:
                dct['date'] = datetime.datetime.strptime(dct['date'], '%Y-%m-%d %H:%M:%S')
            return dct

        page_info_path = os.path.join(self._config.output_path['tools'], 'page_info.json')
        if os.path.exists(page_info_path):
            try:
                with open(page_info_path, 'r', encoding='utf-8') as file:
                    self._page_info = json.load(file, object_hook=convert_datetime)

            except OSError as err:
                print('Can not load page info {}. {}'.format(page_info_path, err))
                raise err
        else:
            self._page_info = {}

    def _save_page_info(self) -> None:
        '''ページ情報ファイルを保存します

        self._config の output_path 属性を利用します

        :raises: OSError ファイルの書き込みに失敗した場合
        '''
        assert hasattr(self._config, 'output_path')

        page_info_path = os.path.join(self._config.output_path['tools'], 'page_info.json')

        try:
            with open(page_info_path, 'w', encoding='utf-8') as file:
                json.dump(self._page_info, file, ensure_ascii=False, indent=2, default=str)
        except OSError as err:
            print('Can not save page info {}. {}'.format(page_info_path, err))
            raise err
