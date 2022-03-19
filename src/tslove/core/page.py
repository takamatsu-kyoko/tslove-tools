'''ページモジュール

T'sLoveのページを扱います
'''

from typing import List, Set

from bs4 import BeautifulSoup  # type: ignore

from tslove.core.web import TsLoveWeb


class Page:
    ''' T'sLoveのページの取得と操作を提供します'''

    @classmethod
    def fetch_from_web(cls, *args, **kwargs):
        '''webからページを取得します

        kwargsで指定したクエリパラメータのうち a は除外されます

        :param args: args[0] クエリパラメータaの値
        :param kwargs: kwargs['param'] 追加のクエリパラメータ
        '''
        param = {
            'm': 'pc',
            'a': args[0],
        }

        if 'param' in kwargs:
            kwargs['param'].pop('a', '')
            param.update(kwargs['param'])
        web = TsLoveWeb.get_instance()
        html = web.get_page(param)

        page = Page()
        page.add_page(html)
        return page

    def __init__(self):
        self._html: List[str] = []
        self.__image_paths: Set[str] = set()
        self.__script_paths: Set[str] = set()

    @property
    def page_count(self) -> int:
        '''htmlのページ数'''
        return len(self._html)

    @property
    def image_paths(self) -> Set[str]:
        '''imgタグのsrcの内容の集合'''
        return self.__image_paths

    @property
    def script_paths(self) -> Set[str]:
        '''scriptタグのsrcの内容の集合'''
        return self.__script_paths

    def add_page(self, html: str):
        '''ページを追加します

        :param html_page: HTMLページ
        '''
        self._html.append(html)
        self._parse(BeautifulSoup(html, 'html.parser'))

    def get_html_page(self, page_num: int) -> str:
        '''htmlページの内容を取得します

        :param page_num: ページ番号
        :return: htmlページの内容
        '''
        return self._html[page_num]

    def _parse(self, soup: BeautifulSoup) -> None:
        '''ページをパースしてプロパティをセットします'''

        for img_tag in soup.find_all('img'):
            self.__image_paths.add(img_tag['src'])

        for script_tag in soup.find_all('script', src=True):
            self.__script_paths.add(script_tag['src'])
