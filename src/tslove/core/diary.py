'''日記モジュール

日記ページと日記に関連する機能を扱います
'''

import re
from datetime import datetime

from bs4 import BeautifulSoup  # type: ignore

from tslove.core.web import TsLoveWeb
from tslove.core.page import Page
from tslove.core.exception import NoSuchDiaryError


class DiaryPage(Page):
    '''日記ページの取得と操作を提供します'''

    @classmethod
    def fetch_from_web(cls, *args, **kwargs):
        '''webから日記ページを取得します

        :param args: args[0] diary_id
        '''
        param = {
            'm': 'pc',
            'a': 'page_fh_diary',
            'target_c_diary_id': args[0],
            'order': 'asc',
            'page_size': 100
        }
        web = TsLoveWeb.get_instance()
        html = web.get_page(param)

        error_pattern = re.compile(r'<td>該当する日記が見つかりません。</td>')
        if error_pattern.search(html):
            raise NoSuchDiaryError

        page = DiaryPage()
        page.add_page(html)
        page.parse()
        return page

    @classmethod
    def read_from_file(cls, file):
        '''ファイルオブジェクトから日記ページを取得します。

        :param file: ファイルオブジェクト'''
        html = file.read()

        page = DiaryPage()
        page.add_page(html)
        page.parse()
        return page

    def __init__(self):
        super().__init__()
        self.__title: str = ''
        self.__date: datetime = None
        self.__prev_diary_id: str = None

    @property
    def title(self):
        '''日記のタイトル'''
        return self.__title

    @property
    def date(self):
        '''日記の作成時刻'''
        return self.__date

    @property
    def prev_diary_id(self):
        '''一つ前の日記のdiary_id'''
        return self.__prev_diary_id

    @property
    def soup0(self) -> BeautifulSoup:
        '''0番目のsoup'''
        # TODO コンテンツ書き換えの仕組みを考えたら廃止します
        return self._soup[0]

    def parse(self):
        '''日記ページをパースしてプロパティをセットします'''
        for soup in self._soup:
            self.__title = str(soup.find('p', class_='heading').get_text(strip=True))

            date_str = str(soup.find('div', class_='dparts diaryDetailBox').div.dl.dt.get_text(strip=True))
            self.__date = datetime.strptime(date_str, '%Y年%m月%d日%H:%M')

            prev_paragraph = soup.find('p', class_='prev')
            if prev_paragraph:
                pattern = re.compile(r'target_c_diary_id=(?P<id>[0-9]+)')
                result = pattern.search(prev_paragraph.a['href'])
                if result:
                    self.__prev_diary_id = result.group('id')

    def write_to_file(self, file):
        '''ファイルへ書き出します

        :param file: ファイルオブジェクト
        '''
        file.write(self._soup[0].prettify(formatter=None))
