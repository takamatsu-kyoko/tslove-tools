'''ダンプアプリケーションの基本的な機能を提供します'''

import datetime
import getpass
import json
import os
import re
from typing import Any, List, Tuple

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

        self._config の show_session_id, php_session_id, echo_password 属性を利用します

        :return: ログインに成功した場合 True
        '''
        assert hasattr(self._config, 'show_session_id')
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

            if self._web.login(username, password):
                if self._config.show_session_id:
                    print('PHP_SESSION_ID: {}'.format(self._web.php_session_id))
                return True

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

    def _dump_image(self, src_path: str, dst_path: str, overwrite=False) -> None:
        '''画像を取得します

        img.phpを利用する場合オリジナルの画像サイズで取得するためにパラメータを組み立て直しています

        :param src_path: 取得元のパス
        :param dst_path: 保存先のパス
        :param overwrite: 画像を上書きする場合 True
        :raise: WebAccessError 画像の取得に失敗した場合
        :raise: OSError 画像の保存に失敗した場合
        :raise: ValueError 取得元のパスからファイル名を取得出来なかった場合
        '''
        pattern = re.compile(r'filename=(?P<filename>[^&;?]+)')

        if os.path.exists(dst_path) and overwrite is False:
            return

        if 'img.php' in src_path:
            result = pattern.search(src_path)
            if result:
                params = {'m': 'pc',
                          'filename': result.group('filename')
                          }
                image = self._web.get_image('img.php', params)
            else:
                raise ValueError('Src filename not match')
        else:
            image = self._web.get_image(src_path)

        image.save(dst_path)

    @staticmethod
    def _find_filename_from_src_path(path: str) -> str:
        '''imgタグやスタイルシート内のパスからファイル名を見つけます

        pathにimg_skin.phpが含まれる場合はクエリパラメータからimage_filenameの値を
        pathにimg.phpが含まれる場合はクエリパラメータからfilenameの値を抜き出します
        それ以外あるいは該当のクエリパラメータが存在しない場合はbasenameを返します

        :param path: パス
        :return: ファイル名
        '''
        img_pattern = re.compile(r'./img\.php.+filename=(?P<filename>[^&;?]+)')
        img_skin_pattern = re.compile(r'./img_skin\.php.+image_filename=(?P<filename>[^&;?]+)')

        result = img_pattern.search(path)
        if result:
            return result.group('filename')

        result = img_skin_pattern.search(path)
        if result:
            return result.group('filename')

        return os.path.basename(path)

    def _dump_stylesheet(self) -> None:
        '''スタイルシートをダンプします

        self._config の output_path 属性を利用します

        :raises: WebAccessError スタイルシート本文の取得に失敗した場合
        :raises: OSError ファイルの出力に失敗した場合
        '''
        assert hasattr(self._config, 'output_path')

        file_name = os.path.join(self._config.output_path['stylesheet'], 'tslove.css')
        if os.path.exists(file_name):
            return

        try:
            stylesheet = self._web.get_stylesheet()
            for src, dst in self.__create_stylesheet_image_path_list(stylesheet):
                try:
                    self._dump_image(src, dst)
                except (WebAccessError, OSError, ValueError) as err:
                    print('Can not dump image {} -> {}. {}'.format(src, dst, err))
                    continue

            with open(file_name, 'w', encoding='utf-8') as file:
                for line in stylesheet.splitlines():
                    result = DumpApp.STYLESHEET_URL_PATTERN.search(line)
                    if result:
                        old_path = result.group('path')
                        new_path = './' + self._find_filename_from_src_path(old_path)
                        line = line.replace(old_path, new_path)
                    file.write(line + '\n')

        except (WebAccessError, OSError) as err:
            print('Can not get stylesheet. {}'.format(err))
            raise err

    def __create_stylesheet_image_path_list(self, stylesheet: str) -> List[Tuple[str, str]]:
        '''スタイルシート中の画像の取得元・保存先のリストを作成します

        self._config の output_path 属性を利用します

        :param stylesheet: スタイルシートの内容
        :return: 画像の取得元・保存先のタプルのリスト
        '''
        assert hasattr(self._config, 'output_path')

        output_path = self._config.output_path['stylesheet']
        exclude_path = ['./skin/default/img/marker.gif']

        path_list = []
        for line in stylesheet.splitlines():
            result = DumpApp.STYLESHEET_URL_PATTERN.search(line)
            if result:
                src_path = result.group('path')
                if src_path not in exclude_path:
                    dst_path = os.path.join(output_path, self._find_filename_from_src_path(src_path))
                    path_list.append((src_path, dst_path))

        return path_list

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
