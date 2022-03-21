'''T's LOVEの日記を一括してダウンロードするプログラム'''

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional, TypedDict, Set, List, Tuple

from bs4 import BeautifulSoup  # type: ignore
from PIL import Image  # type: ignore

from tslove.core.page import Page
from tslove.core.diary import DiaryPage
from tslove.core.exception import WebAccessError
from tslove.dumpapp import DumpApp


class OutputPath(TypedDict):
    '''ダンプの出力先'''
    base: str
    stylesheet: str
    image: str
    script: str
    tools: str


@dataclass
class Config:
    '''コンフィグ'''
    diary_id_from: Optional[str]
    diary_id_to: Optional[str]
    output_path: OutputPath
    echo_password: bool
    show_session_id: bool
    php_session_id: Optional[str] = None


class DiaryDumpApp(DumpApp):  # pylint: disable=R0903
    '''diarydump のアプリケーションクラス'''

    INTERVAL_SHORT = 10
    INTERVAL_LONG = 20
    INTERVAL_CHANGE_TIMING = 5

    DIARY_ID_PATTERN = re.compile(r'\./\?m=pc&a=page_fh_diary&target_c_diary_id=(?P<id>[0-9]+)')

    def __init__(self) -> None:
        super().__init__()
        self._config = self._setup_config()

    @staticmethod
    def _setup_config() -> Config:
        '''コンフィグを生成します

        :return: Configオブジェクト
        '''
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', '--from', help='diary_id to start', metavar='<id>', type=int, default=None)
        parser.add_argument('-t', '--to', help='diary_id to end', metavar='<id>', type=int, default=None)
        parser.add_argument('-o', '--output', help='destination to dump. (default ./dump)', metavar='<PATH>', default='./dump')
        parser.add_argument('--echo-password', help='display password on screen(DANGER)', action='store_true')
        parser.add_argument('--show-session-id', help='for debug', action='store_true')
        args = parser.parse_args()

        diary_id_from, diary_id_to = vars(args)['from'], args.to  # from is keyword
        if diary_id_from and diary_id_to and diary_id_from < diary_id_to:
            diary_id_from, diary_id_to = diary_id_to, diary_id_from

        base = os.path.join(args.output)
        config = Config(
            echo_password=args.echo_password,
            show_session_id=args.show_session_id,
            diary_id_from=str(diary_id_from) if diary_id_from else None,
            diary_id_to=str(diary_id_to) if diary_id_to else None,
            output_path={
                'base': base,
                'stylesheet': os.path.join(base, 'stylesheet'),
                'image': os.path.join(base, 'images'),
                'script': os.path.join(base, 'scripts'),
                'tools': os.path.join(base, 'tslove-tools')
            }
        )
        return config

    @staticmethod
    def _check_first_diary_id() -> str:
        '''最初にダウンロードする日記を取得します

        :return: diary_id or None
        :raises: WebAccessError プロフィールページの取得に失敗した場合
        :raises: ValueError diary_idの取得に失敗した場合
        '''
        try:
            profile_page = BeautifulSoup(Page.fetch_from_web('page_h_prof')[0], 'html.parser')
            diary_list = profile_page.find('ul', class_='articleList')
            result = DiaryDumpApp.DIARY_ID_PATTERN.match(diary_list.a['href'])
            if result:
                return result.group('id')
        except WebAccessError as err:
            print('Can not get first diary id. {}'.format(err))
            raise err

        raise ValueError('Diary id not match.')

    def _output_index(self) -> None:
        '''インデックスファイルを出力します

        :rises: OSError ファイルの書き込みに失敗した場合
        '''
        template = '''
        <!DOCTYPE html>
        <html>
        <head>
        <title>Index of dialy</title>
        <meta charset="utf-8"/>
        </head>
        <body>
        <h1>Index of dialy</h1>
        <table>
        <tr><th>Date</th><th>Title</th></tr>
        </table>
        </body>
        </html>
        '''

        soup = BeautifulSoup(template, 'html.parser')
        table_tag = soup.table

        for diary_id in sorted(self._page_info.keys(), key=int, reverse=True):
            tr_tag = soup.new_tag('tr')
            date_td_tag = soup.new_tag('td')
            date_td_tag.string = self._page_info[diary_id]['date'].strftime('%Y年%m月%d日%H:%M')
            tr_tag.append(date_td_tag)
            title_td_tag = soup.new_tag('td')
            title_a_tag = soup.new_tag('a')
            title_a_tag['href'] = './{}.html'.format(self._page_info[diary_id]['diary_id'])
            title_a_tag.string = self._page_info[diary_id]['title']
            title_td_tag.append(title_a_tag)
            tr_tag.append(title_td_tag)
            table_tag.append(tr_tag)

        file_name = os.path.join(self._config.output_path['base'], 'index.html')
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(soup.prettify(formatter=None))

    def _dump_diary(self, diary_id: str, file_name: str) -> dict:
        '''日記をダンプします

        :param diary_id: diary_id
        :param filename: 出力先ファイル名
        :return: ページ情報
        :rises: WebAccessError 日記の取得に失敗した場合
        :rises: OSError ファイルの書き込みに失敗した場合
        '''
        diary_page = DiaryPage.fetch_from_web(diary_id)

        for src, dst in self.__create_diary_image_path_list(diary_page.image_paths):
            try:
                self._dump_image(src, dst)
            except (WebAccessError, OSError, ValueError) as err:
                print('Can not dump image {} -> {}. {}'.format(src, dst, err))
                continue

        script_paths = diary_page.script_paths
        self._fetch_scripts(script_paths)

        soup = BeautifulSoup(diary_page[0], 'html.parser')

        self.__remove_script(soup)
        self.__remove_form_items(soup)
        self.__fix_link(soup)

        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(soup.prettify(formatter=None))

        page_info = {
            'title': diary_page.title,
            'date': diary_page.date,
            'prev_diary_id': diary_page.prev_diary_id,
            'diary_id': diary_id
        }

        return page_info

    def __create_diary_image_path_list(self, src_paths: Set[str]) -> List[Tuple[str, str]]:
        '''画像の取得元・保存先のリストを作成します

        :params src_paths: 画像の取得元の集合
        :return: 画像の取得元・保存先のタプルのリスト
        '''
        output_path = self._config.output_path['image']

        path_list = []
        for src_path in src_paths:
            if '://' in src_path:
                continue

            dst_path = os.path.join(output_path, self._find_filename_from_src_path(src_path))
            path_list.append((src_path, dst_path))

        return path_list

    @staticmethod
    def __remove_script(soup: BeautifulSoup) -> None:
        '''ページからスクリプトを除去します

        :param soup: ページ
        '''
        script_tags = soup.find_all('script')
        for script_tag in script_tags:
            if script_tag.has_attr('src'):
                src = script_tag['src']
                if src.startswith('./js/prototype.js') or src.startswith('./js/Selection.js') or src == './js/comment.js':
                    script_tag.decompose()
            else:
                if 'url2cmd' not in script_tag.string:
                    script_tag.decompose()

        a_tags_with_script = soup.find_all('a', onclick=True)
        for a_tag in a_tags_with_script:
            a_tag.decompose()

    @staticmethod
    def __remove_form_items(soup):
        '''ページからフォームアイテムを除去します'''
        div_tag = soup.find('div', id='commentForm')
        if div_tag:
            div_tag.decompose()

        div_tags = soup.find_all('div', class_='operation')
        for div_tag in div_tags:
            div_tag.decompose()

        form_tag = soup.find('form')
        if form_tag:
            form_tag.unwrap()

        input_tags = soup.find_all('input')
        for input_tag in input_tags:
            input_tag.decompose()

    def __fix_link(self, soup: BeautifulSoup) -> None:
        '''ページのリンクを修正します

        :param soup: ページ
        '''
        link_tag = soup.find('link', rel='stylesheet')
        if link_tag:
            link_tag['href'] = './stylesheet/tslove.css'

        a_tags_to_diary_list = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=page_fh_diary_list.*'))
        for a_tag_to_diary_list in a_tags_to_diary_list:
            a_tag_to_diary_list['href'] = './index.html'
            del a_tag_to_diary_list['rel']
            del a_tag_to_diary_list['target']

        a_tags_to_dialy = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=page_fh_diary.*'))
        for a_tag_to_dialy in a_tags_to_dialy:
            result = DiaryDumpApp.DIARY_ID_PATTERN.match(a_tag_to_dialy['href'])
            if result:
                diary_id = result.group('id')
                a_tag_to_dialy['href'] = './{}.html'.format(diary_id)
            else:
                a_tag_to_dialy['href'] = '#'
            del a_tag_to_dialy['rel']
            del a_tag_to_dialy['target']

        a_tags_to_top = soup.find_all('a', href='./')
        for a_tag_to_top in a_tags_to_top:
            a_tag_to_top['href'] = './index.html'
            del a_tag_to_top['rel']
            del a_tag_to_top['target']

        a_tags_to_action = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=.+'))
        for a_tag_to_action in a_tags_to_action:
            a_tag_to_action['href'] = '#'
            del a_tag_to_action['rel']
            del a_tag_to_action['target']

        a_tags_to_img = soup.find_all('a', href=re.compile(r'^(\./)?img.php.+'))
        for a_tag_to_img in a_tags_to_img:
            a_tag_to_img['href'] = './images/' + self._find_filename_from_src_path(a_tag_to_img['href'])

        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            path = os.path.join('./images/', self._find_filename_from_src_path(img_tag['src']))
            if 'w=120&h=120' in img_tag['src']:
                target_file = os.path.join(self._config.output_path['base'], path)

                if os.path.exists(target_file):
                    image = Image.open(target_file)
                    if image.size[0] == image.size[1]:
                        img_tag['width'] = 120
                        img_tag['height'] = 120
                    elif image.size[0] > image.size[1]:
                        img_tag['width'] = 120
                    else:
                        img_tag['height'] = 120
                else:
                    img_tag['width'] = 120
                    img_tag['height'] = 120
            img_tag['src'] = path

        for script_tag in soup.find_all('script', src=True):
            script_tag['src'] = 'scripts/' + os.path.basename(script_tag['src'])

    def run(self) -> int:
        '''アプリケーション処理本体

        :return: 正常終了時 0
        '''
        # TODO 起動メッセージ(バージョン)を画面に表示する

        if not self._login():
            print('Login failed.')
            return 1

        # TODO ログインの成功とこの後の進捗を画面に表示する
        try:
            self._prepare_directories()
            self._dump_stylesheet()
            self._load_page_info()
            if self._config.diary_id_from:
                diary_id = self._config.diary_id_from
            else:
                diary_id = self._check_first_diary_id()
        except (WebAccessError, OSError, ValueError):
            return 1

        interval = 0  # 初回のダンプではインターバルを取らない
        without_retry = 0
        dump_process = {
            'page_info': 0,
            'local': 0,
            'remote': 0
        }
        re_pattern = {
            'next_diary_id': re.compile(r'\./(?P<id>[0-9]+).html')
        }

        while diary_id:
            try:  # KeyBoardinterrupt
                file_name = os.path.join(self._config.output_path['base'], '{}.html'.format(diary_id))
                if os.path.exists(file_name):
                    if diary_id in self._page_info:
                        source = 'page_info'
                        page_info = self._page_info[diary_id]
                        dump_process[source] += 1
                    else:
                        source = 'local'
                        diary_page = DiaryPage(re_pattern)  # type: ignore

                        try:
                            with open(file_name, 'r', encoding='utf-8') as file:
                                diary_page.append(file.read())
                        except OSError as err:
                            print('Processing diary id {} failed. (local) {}'.format(diary_id, err))
                            return 1

                        page_info = {
                            'title': diary_page.title,
                            'date': diary_page.date,
                            'prev_diary_id': diary_page.prev_diary_id,
                            'diary_id': diary_id
                        }
                        dump_process[source] += 1
                else:
                    source = 'remote'

                    time.sleep(interval)
                    if interval < DiaryDumpApp.INTERVAL_SHORT:
                        interval = DiaryDumpApp.INTERVAL_LONG

                    retry_count = self._web.total_retries

                    try:
                        page_info = self._dump_diary(diary_id, file_name)
                    except (WebAccessError, OSError) as err:
                        print('Processing diary id {} failed. {}'.format(diary_id, err))
                        return 1

                    dump_process[source] += 1

                    if self._web.total_retries == retry_count:
                        without_retry += 1
                    else:
                        without_retry = 0

                    if interval != DiaryDumpApp.INTERVAL_SHORT and without_retry > DiaryDumpApp.INTERVAL_CHANGE_TIMING:
                        print('Interval changes to {} sec.'.format(DiaryDumpApp.INTERVAL_SHORT))
                        interval = DiaryDumpApp.INTERVAL_SHORT
                    if interval != DiaryDumpApp.INTERVAL_LONG and without_retry <= DiaryDumpApp.INTERVAL_CHANGE_TIMING:
                        print('Interval changes to {} sec.'.format(DiaryDumpApp.INTERVAL_LONG))
                        interval = DiaryDumpApp.INTERVAL_LONG

                print('diary id {} ({}:{}) processed. ({})'.format(diary_id,
                                                                   page_info['date'].strftime('%Y-%m-%d'),
                                                                   page_info['title'],
                                                                   source))

                if source != 'page_info':
                    self._page_info[diary_id] = page_info

                if diary_id == self._config.diary_id_to or page_info['prev_diary_id'] is None:
                    break

                diary_id = page_info['prev_diary_id']

            except KeyboardInterrupt:
                # TODO 中断したことを画面に表示する
                break
        try:
            self._save_page_info()
        except OSError:
            pass

        try:
            self._output_index()
        except OSError as err:
            print('Can not save index file. {}'.format(err))
            return 1

        if dump_process['page_info']:
            print('done. (skip {} diaries)'.format(dump_process['page_info']))
        else:
            print('done.')

        return 0


def main():
    '''エントリポイント'''

    the_app = DiaryDumpApp()
    result = the_app.run()

    sys.exit(result)


if __name__ == "__main__":
    main()
