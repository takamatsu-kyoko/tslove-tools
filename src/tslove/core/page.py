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

    @classmethod
    def read_from_file(cls, file):
        '''ファイルオブジェクトからページを取得します

        :param file: ファイルオブジェクト'''
        html = file.read()

        page = Page()
        page.add_page(html)
        return page

    def __init__(self):
        self._html: List[str] = []
        self._soup: List[BeautifulSoup] = []

    @property
    def page_count(self) -> int:
        '''htmlのページ数'''
        return len(self._html)

    def add_page(self, html: str):
        '''ページを追加します

        :param html_page: HTMLページ
        '''
        self._html.append(html)
        self._soup.append(BeautifulSoup(html, 'html.parser'))

    def get_html_page(self, page_num: int) -> str:
        '''htmlページの内容を取得します

        :param page_num: ページ番号
        :return: htmlページの内容
        '''
        return self._html[page_num]

    def list_image_path(self) -> Set[str]:
        '''imgタグのsrcの内容をリストします

        :return: imgタグのsrc
        '''
        path: Set[str] = set()
        for soup in self._soup:
            for img_tag in soup.find_all('img'):
                path.add(img_tag['src'])
        return path

    def list_script_path(self) -> Set[str]:
        '''scriptタグのsrcの内容をリストします

        :return: scriptタグのsrc
        '''
        path: Set[str] = set()
        for soup in self._soup:
            for script_tag in soup.find_all('script', src=True):
                path.add(script_tag['src'])
        return path

    def write_to_file(self, file):
        '''ファイルへ書き出します

        :param file: ファイルオブジェクト
        '''
        raise NotImplementedError
