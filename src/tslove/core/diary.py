'''日記モジュール

日記ページと日記に関連する機能を扱います
'''

import re
from datetime import datetime
from typing import Optional, TypedDict

from bs4 import BeautifulSoup  # type: ignore

from tslove.core.web import TsLoveWeb
from tslove.core.page import Page
from tslove.core.exception import NoSuchDiaryError


class DiaryRegexPatterns(TypedDict):
    '''DiaryPageの正規表現'''
    prev_diary_id: re.Pattern


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
        page.append(html)
        return page

    def __init__(self, re_pattern: Optional[DiaryRegexPatterns] = None):
        super().__init__()
        self.__title: str = ''
        self.__date: Optional[datetime] = None
        self.__prev_diary_id: Optional[str] = None
        self.__re_pattern: DiaryRegexPatterns = {
            'prev_diary_id': re.compile(r'target_c_diary_id=(?P<id>[0-9]+)')
        }

        if re_pattern:
            self.__re_pattern.update(re_pattern)  # type: ignore # https://github.com/python/mypy/issues/6462 ?

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

    def _parse(self, soup: BeautifulSoup):
        '''日記ページをパースしてプロパティをセットします'''
        super()._parse(soup)

        if not self.__title:
            self.__title = str(soup.find('p', class_='heading').get_text(strip=True))

        if not self.__date:
            date_str = str(soup.find('div', class_='dparts diaryDetailBox').div.dl.dt.get_text(strip=True))
            self.__date = datetime.strptime(date_str, '%Y年%m月%d日%H:%M')

        if not self.__prev_diary_id:
            prev_paragraph = soup.find('p', class_='prev')
            if prev_paragraph:
                pattern = self.__re_pattern['prev_diary_id']
                result = pattern.search(prev_paragraph.a['href'])
                if result:
                    self.__prev_diary_id = result.group('id')
